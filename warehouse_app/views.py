from django.shortcuts import render, redirect
from django.db import models
from .models import Nomenclature
from .models import ProductBatch
from .models import Operation
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from .forms import NomenclatureForm, WarehouseDeductionForm
from warehouse_app.models import Warehouse
from warehouse_app.forms import ProductBatchForm

from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

def index(request):
    return render(request, 'warehouse_app/index.html')

@login_required
def nomenclature_list(request):
    # Для оператора и админа разрешаем добавление новой позиции
    can_add = request.user.has_perm('warehouse_app.add_nomenclature')
    
    query = request.GET.get('q', '')
    if query:
        items = Nomenclature.objects.filter(
            models.Q(code__icontains=query) | models.Q(name__icontains=query)
        )
    else:
        items = Nomenclature.objects.all()

    return render(request, 'warehouse_app/nomenclature_list.html', {
        'items': items,
        'query': query,
        'can_add': can_add,  # передаём флаг в шаблон
    })


def productbatch_list(request):
    query = request.GET.get('q', '')
    if query:
        items = ProductBatch.objects.filter(
            models.Q(batch_number__icontains=query) |
            models.Q(nomenclature__name__icontains=query)
        )
    else:
        batches = ProductBatch.objects.all()
    return render(
        request,
        'warehouse_app/productbatch_list.html',
        {
            'batches': batches,
            'query': query,
        }
    )

def operation_list(request):
    query = request.GET.get('q', '')
    if query:
        items = Operation.objects.filter(
            models.Q(batch__batch_number__icontains=query) |
            models.Q(batch__nomenclature__name__icontains=query)
        )
    else:
        operations = Operation.objects.all()
    return render(
        request,
        'warehouse_app/operation_list.html',
        {
            'operations': operations,
            'query': query,
        }
    )

@login_required
@permission_required('warehouse_app.add_nomenclature', raise_exception=True)
def nomenclature_add(request):
    if request.method == 'POST':
        form = NomenclatureForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('nomenclature_list')
    else:
        form = NomenclatureForm()
    return render(request, 'warehouse_app/nomenclature_add.html', {'form': form})


def warehouse_list(request):
    warehouses = Warehouse.objects.select_related('nomenclature').all()
    return render(
        request,
        'warehouse_app/warehouse_list.html',
        {
            'warehouses': warehouses
        }
    )


def productbatch_create(request):
    if request.method == "POST":
        form = ProductBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.reception_date = None  # партия оформлена, но не принята
            batch.save()
            return redirect("productbatch_list")
    else:
        form = ProductBatchForm()

    return render(
        request,
        "warehouse_app/productbatch_form.html",
        {
            "form": form
        }
    )

@require_POST
def productbatch_receive(request, batch_id):
    batch = get_object_or_404(ProductBatch, pk=batch_id)
    result = batch.receive(note="Принятие через интерфейс")
    messages.success(request, result)
    return redirect("productbatch_list")


from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

def warehouse_deduction(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

    if request.method == "POST":
        form = WarehouseDeductionForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data['quantity']
            if qty > warehouse.current_weight_kg:
                messages.error(request, "Нельзя списать больше, чем есть на складе")
            else:
                # создаём операцию списания
                Operation.objects.create(
                    batch=None,  # или привязать к партии, если нужно
                    operation_type="deduction",
                    quantity=qty,
                    note=form.cleaned_data.get('note', ''),
                    reason=form.cleaned_data['reason'],
                    document=form.cleaned_data.get('document', ''),
                )
                # обновляем склад
                warehouse.current_weight_kg -= qty
                warehouse.save()
                messages.success(request, f"Списание {qty} кг выполнено")
            return redirect('warehouse_list')
    else:
        form = WarehouseDeductionForm()

    return render(request, 'warehouse_app/warehouse_deduction_form.html', {
        'warehouse': warehouse,
        'form': form
    })


# warehouse_app/views.py
import openpyxl
from django.http import HttpResponse
from .models import Operation, Warehouse
from django.contrib.auth.decorators import login_required

@login_required
def export_data(request):
    if request.method == "POST":
        export_type = request.POST.get("export_type")

        # Создаём рабочую книгу
        wb = openpyxl.Workbook()
        ws = wb.active

        if export_type == "operations":
            ws.title = "Журнал операций"
            # Заголовки
            ws.append([
                "ID", "Тип операции", "Номер партии", "Продукция",
                "Дата операции", "Количество (кг)", "Причина", "Документ", "Примечание"
            ])
            operations = Operation.objects.all()
            for op in operations:
                batch_number = op.batch.batch_number if op.batch else "—"
                product_name = op.batch.nomenclature.name if op.batch else "—"
                ws.append([
                    op.id,
                    op.get_operation_type_display(),
                    batch_number,
                    product_name,
                    op.operation_date.strftime("%Y-%m-%d %H:%M:%S"),
                    op.quantity,
                    getattr(op, 'reason', ''),
                    getattr(op, 'document', ''),
                    op.note or ''
                ])
        elif export_type == "warehouse":
            ws.title = "Складские остатки"
            ws.append(["Код продукции", "Наименование", "Текущий остаток (кг)"])
            warehouses = Warehouse.objects.select_related('nomenclature').all()
            for w in warehouses:
                ws.append([w.nomenclature.code, w.nomenclature.name, w.current_weight_kg])
        else:
            return HttpResponse("Неверный тип экспорта", status=400)

        # Подготовка ответа
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"{export_type}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'
        wb.save(response)
        return response

    # GET-запрос — показать страницу с выбором экспорта
    return render(request, 'warehouse_app/export_page.html')
