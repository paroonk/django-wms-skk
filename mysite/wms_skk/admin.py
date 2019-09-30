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
        import_id_fields = ('plant_id',)
        skip_unchanged = True
        report_skipped = False


class PlantAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = PlantResource
    list_display = ('plant_id', 'description')
    list_editable = ('description',)

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class BufferResource(resources.ModelResource):
    class Meta:
        model = Buffer
        import_id_fields = ('buffer_id',)
        skip_unchanged = True
        report_skipped = False


class BufferAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = BufferResource
    list_display = ('buffer_id', 'buffer_plant_list')

    def buffer_plant_list(self, obj):
        return ", ".join([plant.plant_id for plant in obj.buffer_for_plant.all()])

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        import_id_fields = ('product_id',)
        skip_unchanged = True
        report_skipped = False


class ProductAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = ProductResource
    list_display = ('product_id', 'name_th', 'name_en', 'plant', 'qty_limit', 'bg_color', 'font_color', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_total', 'qty_storage_avail')
    list_filter = ['plant', 'qty_limit']
    search_fields = ['product_id', 'name_th', 'name_en']

    fieldsets = [
        (None, {'fields': ['product_id']}),
        ('Name', {'fields': ['name_th', 'name_en']}),
        ('Description', {'fields': ['plant', 'qty_limit', 'bg_color', 'font_color']}),
    ]

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class ColumnResource(resources.ModelResource):
    class Meta:
        model = Column
        import_id_fields = ('column_id',)
        skip_unchanged = True
        report_skipped = False


class ColumnAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = ColumnResource
    list_display = ('column_id', 'is_inventory', 'for_product', 'for_buffer')
    list_per_page = 50
    list_filter = ['is_inventory', 'for_product', 'for_buffer']
    search_fields = ['column_id', 'for_product', 'for_buffer']

    fieldsets = [
        (None, {'fields': ['column_id']}),
        ('Description', {'fields': ['is_inventory', 'for_product', 'for_buffer']}),
    ]

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class CoordinateResource(resources.ModelResource):
    class Meta:
        model = Coordinate
        import_id_fields = ('coor_id',)
        skip_unchanged = True
        report_skipped = False


class CoordinateAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = CoordinateResource
    list_display = ('coor_id', 'layout_col', 'layout_row', 'coor_x', 'coor_y')
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
        import_id_fields = ('storage_id',)
        skip_unchanged = True
        report_skipped = False


class StorageAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = StorageResource
    list_display = ('storage_id', 'coor_id', 'coor_x', 'coor_y', 'is_inventory', 'storage_for',
                    'have_inventory', 'inv_product', 'name_th', 'name_en', 'inv_qty', 'lot_name', 'created_on', 'updated_on', 'bg_color', 'font_color')
    list_per_page = 50
    list_filter = ['created_on', 'updated_on', 'have_inventory', 'inv_product', 'is_inventory', 'zone', 'col', 'row']
    search_fields = ['storage_id', 'storage_for', 'lot_name']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvProductionPlanResource(resources.ModelResource):
    class Meta:
        model = AgvProductionPlan
        skip_unchanged = True
        report_skipped = False


class AgvProductionPlanAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = AgvProductionPlanResource
    list_display = ('id', 'product_id', 'qty_total', 'qty_remain', 'lot_name', 'percent_complete')
    list_editable = ('product_id', 'qty_total', 'qty_remain', 'lot_name')
    list_display_links = None
    list_per_page = 50
    list_filter = ['product_id', 'lot_name']
    search_fields = ['product_id', 'lot_name']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class RobotQueueResource(resources.ModelResource):
    class Meta:
        model = RobotQueue
        skip_unchanged = True
        report_skipped = False


class RobotQueueAdmin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = RobotQueueResource
    list_display = ('id', 'robot_no', 'product_id', 'qty_act', 'updated')
    list_editable = ('robot_no', 'product_id', 'qty_act', 'updated')
    list_display_links = None
    list_per_page = 50
    list_filter = ['robot_no', 'product_id']
    search_fields = ['product_id']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvQueue1Resource(resources.ModelResource):
    class Meta:
        model = AgvQueue1
        skip_unchanged = True
        report_skipped = False


class AgvQueue1Admin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = AgvQueue1Resource
    list_display = ('id', 'product_id', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id', 'pick_col', 'pick_row', 'place_id', 'place_col', 'place_row', 'mode')
    list_per_page = 50
    list_filter = ['mode', 'lot_name', 'product_id']
    search_fields = ['product_id']

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


class AgvTransfer1Resource(resources.ModelResource):
    class Meta:
        model = AgvTransfer1
        skip_unchanged = True
        report_skipped = False


class AgvTransfer1Admin(ImportExportMixin, SimpleHistoryAdmin):
    resource_class = AgvTransfer1Resource
    list_display = ('id', 'status', 'step', 'x_nav', 'y_nav', 'beta_nav', 'pause', 'pattern', 'qty', 'x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4', 'x5', 'y5')
    list_editable = ('status', 'step', 'pause', 'pattern')
    # list_display_links = None
    list_per_page = 50

    def get_import_formats(self):
        return [base_formats.XLSX]

    def get_export_formats(self):
        return [base_formats.XLSX]


admin.site.register(Plant, PlantAdmin)
admin.site.register(Buffer, BufferAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Column, ColumnAdmin)
admin.site.register(Coordinate, CoordinateAdmin)
admin.site.register(Storage, StorageAdmin)
admin.site.register(AgvProductionPlan, AgvProductionPlanAdmin)
admin.site.register(RobotQueue, RobotQueueAdmin)
admin.site.register(AgvQueue1, AgvQueue1Admin)
admin.site.register(AgvTransfer1, AgvTransfer1Admin)
