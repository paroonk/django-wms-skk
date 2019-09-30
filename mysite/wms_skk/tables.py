import django_filters
import django_tables2 as tables
from django import forms

from .models import *


class ProductDatabaseFilter(django_filters.FilterSet):
    product_id = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Product ID'}))
    name_th = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Thai Name'}))
    name_en = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'English Name'}))

    class Meta:
        model = Product
        fields = ['product_id', 'name_th', 'name_en', 'plant']


class ProductDatabaseTable(tables.Table):
    qty_storage = tables.Column(verbose_name='Storage Qty', orderable=False)
    qty_inventory = tables.Column(verbose_name='Inventory Qty', orderable=False)
    qty_buffer = tables.Column(verbose_name='Buffer Qty', orderable=False)
    qty_misplace = tables.Column(verbose_name='Misplace Qty', orderable=False)
    qty_total = tables.Column(verbose_name='Total Qty', orderable=False)
    qty_storage_avail = tables.Column(verbose_name='Avail. Storage Qty', orderable=False)
    qty_inventory_avail = tables.Column(verbose_name='Avail. Inventory Qty', orderable=False)

    class Meta:
        model = Product
        fields = ['product_id', 'name_th', 'name_en', 'plant', 'qty_limit', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']


class StorageDatabaseFilter(django_filters.FilterSet):
    storage_id = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Storage ID'}))
    storage_for = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Storage For'}))
    inv_product = django_filters.CharFilter(field_name='inv_product__product_id', lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Inventory Product'}))
    name_th = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Thai Name'}))
    lot_name = django_filters.CharFilter(lookup_expr='icontains', widget=forms.TextInput(attrs={'placeholder': 'Lot Name'}))

    class Meta:
        model = Storage
        fields = ['storage_id', 'storage_for', 'inv_product', 'name_th', 'lot_name']


class StorageDatabaseTable(tables.Table):
    storage_for = tables.Column(orderable=False)

    class Meta:
        model = Storage
        fields = ['storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'name_th', 'name_en', 'inv_qty', 'lot_name', 'created_on', 'updated_on']


class ProductLogTable(tables.Table):
    history_date = tables.Column(orderable=False)
    history_change_reason = tables.Column(orderable=False)
    history_type = tables.Column(orderable=False)
    history_user = tables.Column(orderable=False)
    product_id = tables.Column(orderable=False)
    qty_storage = tables.Column(orderable=False)
    qty_inventory = tables.Column(orderable=False)
    qty_buffer = tables.Column(orderable=False)
    qty_misplace = tables.Column(orderable=False)
    qty_total = tables.Column(orderable=False)
    qty_storage_avail = tables.Column(orderable=False)
    qty_inventory_avail = tables.Column(orderable=False)


class StorageLogTable(tables.Table):
    history_date = tables.Column(orderable=False)
    history_change_reason = tables.Column(orderable=False)
    history_type = tables.Column(orderable=False)
    history_user = tables.Column(orderable=False)
    storage_id = tables.Column(orderable=False)
    is_inventory = tables.Column(orderable=False)
    storage_for = tables.Column(orderable=False)
    have_inventory = tables.Column(orderable=False)
    inv_product = tables.Column(orderable=False)
    inv_qty = tables.Column(orderable=False)


class AgvProductionPlanLogTable(tables.Table):
    history_date = tables.Column(orderable=False)
    history_change_reason = tables.Column(orderable=False)
    history_type = tables.Column(orderable=False)
    history_user = tables.Column(orderable=False)
    id = tables.Column(orderable=False)
    product_id = tables.Column(orderable=False)
    qty_total = tables.Column(orderable=False)
    qty_remain = tables.Column(orderable=False)
    lot_name = tables.Column(orderable=False)


class RobotQueueLogTable(tables.Table):
    history_date = tables.Column(orderable=False)
    history_change_reason = tables.Column(orderable=False)
    history_type = tables.Column(orderable=False)
    history_user = tables.Column(orderable=False)
    robot_no = tables.Column(orderable=False)
    product_id = tables.Column(orderable=False)
    qty_act = tables.Column(orderable=False)


class AgvQueue1LogTable(tables.Table):
    history_date = tables.Column(orderable=False)
    history_change_reason = tables.Column(orderable=False)
    history_type = tables.Column(orderable=False)
    history_user = tables.Column(orderable=False)
    product_id = tables.Column(orderable=False)
    lot_name = tables.Column(orderable=False)
    qty_act = tables.Column(orderable=False)
    created_on = tables.Column(orderable=False)
    robot_no = tables.Column(orderable=False)
    pick_id = tables.Column(orderable=False)
    place_id = tables.Column(orderable=False)
    mode = tables.Column(orderable=False)


class AgvTransfer1LogTable(tables.Table):
    history_date = tables.Column(orderable=False)
    history_change_reason = tables.Column(orderable=False)
    history_type = tables.Column(orderable=False)
    history_user = tables.Column(orderable=False)
    status = tables.Column(orderable=False)
    step = tables.Column(orderable=False)
    pause = tables.Column(orderable=False)
    pattern = tables.Column(orderable=False)
