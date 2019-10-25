import django_tables2 as tables
from django import forms

from .models import *


class ProductDatabaseTable(tables.Table):
    class Meta:
        model = Product
        fields = ['product_name', 'plant', 'qty_limit', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']


class StorageDatabaseTable(tables.Table):
    class Meta:
        model = Storage
        fields = ['storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'inv_qty', 'lot_name', 'created_on', 'updated_on']


class ProductLogTable(tables.Table):
    history_date = tables.Column()
    history_change_reason = tables.Column()
    history_type = tables.Column()
    history_user = tables.Column()
    product_name = tables.Column()
    qty_storage = tables.Column()
    qty_inventory = tables.Column()
    qty_buffer = tables.Column()
    qty_misplace = tables.Column()
    qty_total = tables.Column()
    qty_storage_avail = tables.Column()
    qty_inventory_avail = tables.Column()


class StorageLogTable(tables.Table):
    history_date = tables.Column()
    history_change_reason = tables.Column()
    history_type = tables.Column()
    history_user = tables.Column()
    storage_id = tables.Column()
    is_inventory = tables.Column()
    storage_for = tables.Column()
    have_inventory = tables.Column()
    inv_product = tables.Column()
    inv_qty = tables.Column()


class AgvProductionPlanLogTable(tables.Table):
    history_date = tables.Column()
    history_change_reason = tables.Column()
    history_type = tables.Column()
    history_user = tables.Column()
    id = tables.Column()
    product_name = tables.Column()
    qty_total = tables.Column()
    qty_remain = tables.Column()
    lot_name = tables.Column()


class RobotQueueLogTable(tables.Table):
    history_date = tables.Column()
    history_change_reason = tables.Column()
    history_type = tables.Column()
    history_user = tables.Column()
    robot_no = tables.Column()
    product_id = tables.Column()
    qty_act = tables.Column()


class AgvQueueLogTable(tables.Table):
    history_date = tables.Column()
    history_change_reason = tables.Column()
    history_type = tables.Column()
    history_user = tables.Column()
    product_name = tables.Column()
    lot_name = tables.Column()
    qty_act = tables.Column()
    created_on = tables.Column()
    robot_no = tables.Column()
    pick_id = tables.Column()
    place_id = tables.Column()
    mode = tables.Column()


class AgvTransferLogTable(tables.Table):
    history_date = tables.Column()
    history_change_reason = tables.Column()
    history_type = tables.Column()
    history_user = tables.Column()
    run = tables.Column()
    status = tables.Column()
    step = tables.Column()
    pause = tables.Column()
    pattern = tables.Column()
