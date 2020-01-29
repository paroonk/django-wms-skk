from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportMixin
from import_export.formats import base_formats
from simple_history.admin import SimpleHistoryAdmin

from .models import *

admin.site.site_url = '/'
admin.AdminSite.site_header = 'WMS Administration'


class PlantResource(resources.ModelResource):
    class Meta:
        model = Plant
        import_id_fields = ['plant_id']
        skip_unchanged = True
        report_skipped = False


class PlantAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = PlantResource
    list_display = ['plant_id', 'description']
    list_editable = ['description']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class BufferResource(resources.ModelResource):
    class Meta:
        model = Buffer
        import_id_fields = ['buffer_id']
        skip_unchanged = True
        report_skipped = False


class BufferAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = BufferResource
    list_display = ['buffer_id', 'buffer_for_plant_list']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        import_id_fields = ['product_name']
        skip_unchanged = True
        report_skipped = False


class ProductAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = ProductResource
    list_display = ['product_name', 'plant', 'qty_limit', 'bg_color', 'font_color', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_total', 'qty_storage_avail']
    list_filter = ['plant', 'qty_limit']
    search_fields = ['product_name']

    fieldsets = (
        (None, {'fields': ['product_name']}),
        ('Description', {'fields': ['plant', 'qty_limit', 'bg_color', 'font_color']}),
    )

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class ColumnResource(resources.ModelResource):
    class Meta:
        model = Column
        import_id_fields = ['column_id']
        skip_unchanged = True
        report_skipped = False


class ColumnAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = ColumnResource
    list_display = ['column_id', 'is_inventory', 'for_product', 'for_buffer']
    list_per_page = 50
    list_filter = ['is_inventory', 'for_product', 'for_buffer']
    search_fields = ['column_id', 'for_product__product_name', 'for_buffer__buffer_id']

    fieldsets = (
        (None, {'fields': ['column_id']}),
        ('Description', {'fields': ['is_inventory', 'for_product', 'for_buffer']}),
    )

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class CoordinateResource(resources.ModelResource):
    class Meta:
        model = Coordinate
        import_id_fields = ['coor_id']
        skip_unchanged = True
        report_skipped = False


class CoordinateAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = CoordinateResource
    list_display = ['coor_id', 'layout_col', 'layout_row', 'coor_x', 'coor_y']
    list_per_page = 50
    list_filter = ['layout_col', 'layout_row']
    search_fields = ['layout_col', 'layout_row']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class StorageResource(resources.ModelResource):
    class Meta:
        model = Storage
        import_id_fields = ['storage_id']
        skip_unchanged = True
        report_skipped = False


class StorageAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = StorageResource
    list_display = ['storage_id', 'coor_id', 'coor_x', 'coor_y', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'inv_qty', 'lot_name', 'created_on', 'updated_on', 'bg_color', 'font_color']
    list_per_page = 50
    list_filter = ['created_on', 'updated_on', 'have_inventory', 'inv_product', 'is_inventory', 'zone', 'col', 'row']
    search_fields = ['storage_id', 'storage_for', 'lot_name']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvProductionPlanAdmin(SimpleHistoryAdmin):
    list_display = ['id', 'product_name', 'qty_total', 'qty_remain', 'lot_name', 'percent_complete']
    list_editable = ['product_name', 'qty_total', 'qty_remain', 'lot_name']
    list_display_links = None
    list_per_page = 50
    list_filter = ['product_name', 'lot_name']
    search_fields = ['product_name', 'lot_name']


class RobotStatusAdmin(SimpleHistoryAdmin):
    list_display = ['robot_no', 'brand', 'qty_act', 'qty_target']


class RobotQueueAdmin(SimpleHistoryAdmin):
    list_display = ['id', 'robot_no', 'product_id', 'qty_act', 'updated']
    list_editable = ['robot_no', 'product_id', 'qty_act', 'updated']
    list_display_links = None
    list_per_page = 50
    list_filter = ['robot_no', 'product_id']
    search_fields = ['product_id']


class AgvQueueAdmin(SimpleHistoryAdmin):
    list_display = ['id', 'product_name', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id', 'pick_col', 'pick_row', 'place_id', 'place_col', 'place_row', 'mode', 'agv_no']
    list_per_page = 50
    list_filter = ['mode', 'lot_name', 'product_name', 'agv_no']
    search_fields = ['product_name']


class AgvTransferAdmin(SimpleHistoryAdmin):
    list_display = [
        'id',
        'run',
        'status',
        'step',
        'x_nav',
        'y_nav',
        'beta_nav',
        'pause',
        'pattern',
        'qty',
        'x1',
        'y1',
        'x2',
        'y2',
        'x3',
        'y3',
        'x4',
        'y4',
        'x5',
        'y5',
        'col1',
        'row1',
        'col2',
        'row2',
        'col3',
        'row3',
        'col4',
        'row4',
        'col5',
        'row5',
    ]
    list_editable = ['run', 'status', 'step', 'pause', 'pattern']
    list_per_page = 50


admin.site.register(Plant, PlantAdmin)
admin.site.register(Buffer, BufferAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Column, ColumnAdmin)
admin.site.register(Coordinate, CoordinateAdmin)
admin.site.register(Storage, StorageAdmin)
admin.site.register(AgvProductionPlan, AgvProductionPlanAdmin)
admin.site.register(RobotStatus, RobotStatusAdmin)
admin.site.register(RobotQueue, RobotQueueAdmin)
admin.site.register(AgvQueue, AgvQueueAdmin)
admin.site.register(AgvTransfer, AgvTransferAdmin)


class ProductHistoryResource(resources.ModelResource):
    class Meta:
        model = Product.history.model
        import_id_fields = ['history_id']
        skip_unchanged = True
        report_skipped = False


class ProductHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProductHistoryResource
    list_display = ['history_id', 'history_date', 'history_type', 'history_change_reason', 'product_name', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
    list_filter = ['history_date']
    search_fields = ['product_name']
    list_per_page = 50

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class StorageHistoryResource(resources.ModelResource):
    class Meta:
        model = Storage.history.model
        import_id_fields = ['history_id']
        skip_unchanged = True
        report_skipped = False


class StorageHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = StorageHistoryResource
    list_display = ['history_id', 'history_date', 'history_type', 'history_change_reason', 'storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'inv_qty']
    list_per_page = 50
    list_filter = ['history_date', 'have_inventory', 'inv_product', 'is_inventory']
    search_fields = ['storage_id']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvProductionPlanHistoryResource(resources.ModelResource):
    class Meta:
        model = AgvProductionPlan.history.model
        import_id_fields = ['history_id']
        skip_unchanged = True
        report_skipped = False


class AgvProductionPlanHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = AgvProductionPlanHistoryResource
    list_display = ['history_id', 'history_date', 'history_type', 'history_change_reason', 'id', 'product_name', 'qty_total', 'qty_remain', 'lot_name']
    list_per_page = 50
    list_filter = ['history_date', 'product_name', 'lot_name']
    search_fields = ['product_name', 'lot_name']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class RobotQueueHistoryResource(resources.ModelResource):
    class Meta:
        model = RobotQueue.history.model
        import_id_fields = ['history_id']
        skip_unchanged = True
        report_skipped = False


class RobotQueueHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = RobotQueueHistoryResource
    list_display = ['history_id', 'history_date', 'history_type', 'history_change_reason', 'id', 'robot_no', 'product_id', 'qty_act']
    list_per_page = 50
    list_filter = ['history_date', 'robot_no', 'product_id']
    search_fields = ['product_id']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvQueueHistoryResource(resources.ModelResource):
    class Meta:
        model = AgvQueue.history.model
        import_id_fields = ['history_id']
        skip_unchanged = True
        report_skipped = False


class AgvQueueHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = AgvQueueHistoryResource
    list_display = ['history_id', 'history_date', 'history_type', 'history_change_reason', 'id', 'product_name', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id', 'place_id', 'mode']
    list_per_page = 50
    list_filter = ['history_date', 'mode', 'lot_name', 'product_name']
    search_fields = ['product_name']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvTransferHistoryResource(resources.ModelResource):
    class Meta:
        model = AgvTransfer.history.model
        import_id_fields = ['history_id']
        skip_unchanged = True
        report_skipped = False


class AgvTransferHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = AgvTransferHistoryResource
    list_display = ['history_id', 'history_date', 'history_type', 'history_change_reason', 'id', 'run', 'status', 'step', 'pause', 'pattern']
    list_per_page = 50
    list_filter = ['history_date']
    search_fields = ['id']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


admin.site.register(Product.history.model, ProductHistoryAdmin)
admin.site.register(Storage.history.model, StorageHistoryAdmin)
admin.site.register(AgvProductionPlan.history.model, AgvProductionPlanHistoryAdmin)
admin.site.register(RobotQueue.history.model, RobotQueueHistoryAdmin)
admin.site.register(AgvQueue.history.model, AgvQueueHistoryAdmin)
admin.site.register(AgvTransfer.history.model, AgvTransferHistoryAdmin)
