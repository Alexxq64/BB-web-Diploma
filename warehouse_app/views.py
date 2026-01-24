from django.shortcuts import render, redirect
from django.db import models
from .models import Nomenclature
from .models import ProductBatch
from .models import Operation
from .models import LiveBatch
from django.contrib.auth.decorators import login_required, permission_required
from .forms import NomenclatureForm, WarehouseDeductionForm
from warehouse_app.models import Warehouse
from warehouse_app.forms import ProductBatchForm

from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

def index(request):
    return render(request, 'warehouse_app/index.html')

from django.core.paginator import Paginator

@login_required
def nomenclature_list(request):
    query = request.GET.get('q', '')

    sort = request.GET.get('sort', 'code')
    direction = request.GET.get('direction', 'asc')
    order_by = sort if direction == 'asc' else f'-{sort}'

    items = Nomenclature.objects.all()

    if query:
        items = items.filter(
            models.Q(code__icontains=query) |
            models.Q(name__icontains=query)
        )

    items = items.order_by(order_by)

    paginator = Paginator(items, 10)
    page_number = request.GET.get('page')
    items_page = paginator.get_page(page_number)

    return render(request, 'warehouse_app/nomenclature_list.html', {
        'items': items_page,
        'query': query,
        'sort': sort,
        'direction': direction,
    })

from datetime import datetime

def productbatch_list(request):
    batches = ProductBatch.objects.all()
    
    # --- Поиск ---
    query = request.GET.get('q', '')
    if query:
        batches = batches.filter(
            models.Q(batch_number__icontains=query) |
            models.Q(nomenclature__name__icontains=query)
        )

    # --- Фильтры по датам ---
    start_production_date = request.GET.get('start_production_date', '')
    end_production_date = request.GET.get('end_production_date', '')
    start_reception_date = request.GET.get('start_reception_date', '')
    end_reception_date = request.GET.get('end_reception_date', '')
    start_expiration_date = request.GET.get('start_expiration_date', '')
    end_expiration_date = request.GET.get('end_expiration_date', '')

    if start_production_date:
        batches = batches.filter(production_date__gte=start_production_date)
    if end_production_date:
        batches = batches.filter(production_date__lte=end_production_date)

    if start_reception_date:
        batches = batches.filter(reception_date__date__gte=start_reception_date)
    if end_reception_date:
        batches = batches.filter(reception_date__date__lte=end_reception_date)

    if start_expiration_date:
        batches = batches.filter(expiration_date__gte=start_expiration_date)
    if end_expiration_date:
        batches = batches.filter(expiration_date__lte=end_expiration_date)

    # --- Сортировка ---
    sort = request.GET.get('sort', 'production_date')
    direction = request.GET.get('direction', 'asc')
    if direction == 'desc':
        sort = '-' + sort
    batches = batches.order_by(sort)

    # --- Пагинация ---
    paginator = Paginator(batches, 10)  # 10 партий на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- Контекст для шаблона ---
    context = {
        'batches': page_obj,
        'query': query,
        'sort': request.GET.get('sort', ''),
        'direction': request.GET.get('direction', ''),
        'start_production_date': start_production_date,
        'end_production_date': end_production_date,
        'start_reception_date': start_reception_date,
        'end_reception_date': end_reception_date,
        'start_expiration_date': start_expiration_date,
        'end_expiration_date': end_expiration_date,
    }

    return render(request, 'warehouse_app/productbatch_list.html', context)


from django.utils.dateparse import parse_date
from datetime import time

def operation_list(request):
    query = request.GET.get('q', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    order_by = request.GET.get('order_by', '-operation_date')
    page_number = request.GET.get('page', 1)

    operations = Operation.objects.all()

    # Фильтр по тексту
    if query:
        operations = operations.filter(
            models.Q(batch__batch_number__icontains=query) |
            models.Q(batch__nomenclature__name__icontains=query)
        )

    # Фильтр по диапазону дат с учётом времени
    start_datetime = None
    end_datetime = None

    if start_date_str:
        # начало дня
        start_dt = parse_date(start_date_str)
        if start_dt:
            start_datetime = datetime.combine(start_dt, time.min)

    if end_date_str:
        # конец дня
        end_dt = parse_date(end_date_str)
        if end_dt:
            end_datetime = datetime.combine(end_dt, time.max)

    if start_datetime and end_datetime:
        operations = operations.filter(operation_date__range=[start_datetime, end_datetime])
    elif start_datetime:
        operations = operations.filter(operation_date__gte=start_datetime)
    elif end_datetime:
        operations = operations.filter(operation_date__lte=end_datetime)

    # Сортировка
    operations = operations.order_by(order_by)

    # Пагинация
    paginator = Paginator(operations, 10)  # 10 записей на страницу
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'warehouse_app/operation_list.html',
        {
            'operations': page_obj,
            'query': query,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'order_by': order_by,
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


from .models import Warehouse


def warehouse_list(request):
    query = request.GET.get('q', '')

    sort = request.GET.get('sort', 'nomenclature__code')
    direction = request.GET.get('direction', 'asc')
    order_by = sort if direction == 'asc' else f'-{sort}'

    warehouses = Warehouse.objects.select_related('nomenclature')

    if query:
        warehouses = warehouses.filter(
            models.Q(nomenclature__code__icontains=query) |
            models.Q(nomenclature__name__icontains=query)
        )

    warehouses = warehouses.order_by(order_by)

    paginator = Paginator(warehouses, 10)
    page_number = request.GET.get('page')
    warehouses_page = paginator.get_page(page_number)

    return render(
        request,
        'warehouse_app/warehouse_list.html',
        {
            'warehouses': warehouses_page,
            'query': query,
            'sort': sort,
            'direction': direction,
        }
    )


@login_required
def productbatch_create(request, batch_id=None):
    if batch_id:
        batch = get_object_or_404(ProductBatch, pk=batch_id)
        form = ProductBatchForm(request.POST or None, instance=batch)
    else:
        batch = None
        form = ProductBatchForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            batch = form.save(commit=False)
            if not batch_id:
                batch.reception_date = None  # новая партия оформлена, но не принята
            batch.save()
            return redirect("productbatch_list")

    return render(
        request,
        "warehouse_app/productbatch_form.html",
        {
            "form": form,
            "batch": batch
        }
    )

@require_POST
def productbatch_receive(request, batch_id):
    batch = get_object_or_404(ProductBatch, pk=batch_id)
    result = batch.receive(note="Принятие через интерфейс")
    messages.success(request, result)
    return redirect("productbatch_list")


from django.utils import timezone

def warehouse_deduction(request, warehouse_id):
    """
    Оформление списания продукции со склада по партиям.
    """
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    
    # Получаем активные партии по этой номенклатуре
    live_batches = LiveBatch.objects.filter(
        product_batch__nomenclature=warehouse.nomenclature
    ).select_related(
        'product_batch', 
        'product_batch__nomenclature'
    ).order_by('product_batch__expiration_date')

    if request.method == "POST":
        # Обработка списания по партиям
        print(f"DEBUG: POST данные batch_ поля: {[f'{k}={v}' for k, v in request.POST.items() if k.startswith('batch_')]}")
        reason = request.POST.get('reason', '').strip()
        document = request.POST.get('document', '').strip()
        note = request.POST.get('note', '').strip()
        
        if not reason:
            messages.error(request, "Укажите причину списания")
            return redirect('warehouse_deduction', warehouse_id=warehouse.id)
        
        operations_created = []
        total_deducted = 0
        batches_processed = []
        
        # Проверяем, что хотя бы одна партия выбрана
        has_selection = False
        for lb in live_batches:
            qty_str = request.POST.get(f'batch_{lb.id}', '').strip()
            if qty_str:  # если строка не пустая
                try:
                    qty = float(qty_str)
                    if qty > 0:
                        has_selection = True
                        break
                except ValueError:
                    continue  # если не число - пропускаем

        if not has_selection:
            messages.error(request, "Выберите хотя бы одну партию для списания")
            return redirect('warehouse_deduction', warehouse_id=warehouse.id)


        for lb in live_batches:
            field_name = f"batch_{lb.id}"
            qty_str = request.POST.get(field_name, '0').strip()
            
            if not qty_str or float(qty_str) <= 0:
                continue
                
            try:
                qty = float(qty_str)
                if qty > lb.current_quantity:
                    messages.error(
                        request, 
                        f"Недостаточно в партии {lb.product_batch.batch_number}. "
                        f"Доступно: {lb.current_quantity:.2f}, запрошено: {qty:.2f}"
                    )
                    return redirect('warehouse_deduction', warehouse_id=warehouse.id)
                
                # Создаём операцию списания для этой партии
                Operation.objects.create(
                    batch=lb.product_batch,
                    nomenclature=warehouse.nomenclature,
                    operation_type="deduction",
                    quantity=qty,
                    reason=reason,
                    document=document,
                    note=note
                )
                
                # Обновляем LiveBatch
                lb.current_quantity -= qty
                if lb.current_quantity == 0:
                    lb.delete()  # партия полностью списана
                else:
                    lb.save()
                
                total_deducted += qty
                batches_processed.append(f"{lb.product_batch.batch_number} ({qty:.2f})")
                
            except ValueError:
                messages.error(request, f"Некорректное количество для партии {lb.product_batch.batch_number}")
                return redirect('warehouse_deduction', warehouse_id=warehouse.id)
        
        # Обновляем общий остаток на складе
        if total_deducted > 0:
            warehouse.current_quantity -= total_deducted
            warehouse.save()
            
            messages.success(
                request,
                f"Списание оформлено. "
                f"Списано {total_deducted:.2f} {warehouse.nomenclature.unit} из {len(batches_processed)} партий. "
                f"Партии: {', '.join(batches_processed)}"
            )
        
        return redirect('warehouse_list')
    
    else:
        # GET-запрос: создаем форму (без поля quantity)
        form = WarehouseDeductionForm()

    return render(request, 'warehouse_app/warehouse_deduction_form.html', {
        'warehouse': warehouse,
        'form': form,
        'live_batches': live_batches,
        'now': timezone.now().date()
    })

# warehouse_app/views.py
import openpyxl
from django.http import HttpResponse
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
                ws.append([w.nomenclature.code, w.nomenclature.name, w.current_quantity])
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
