from django.urls import path

from . import views, sched

app_name = 'wms'
urlpatterns = [
    path('', views.redirect_home, name='home'),
    path('permission_denied/', views.permission_denied, name='permission_denied'),
    path('auto_close', views.AutoCloseView.as_view(), name='auto_close'),

    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    path('layout/', views.LayoutView.as_view(), name='layout'),
    path('layout/<slug:pk>/inv_create/', views.inv_create, name='inv_create'),
    path('layout/<slug:pk>/inv_update/', views.inv_update, name='inv_update'),
    path('layout/<slug:pk>/inv_delete/', views.inv_delete, name='inv_delete'),
    path('layout/<pk>/invcol_update/', views.invcol_update, name='invcol_update'),
    path('layout/<pk>/invcol_delete/', views.invcol_delete, name='invcol_delete'),
    path('layout_debug/', views.LayoutDebugView.as_view(), name='layout_debug'),
    path('layout_debug/<slug:pk>/col_update/', views.col_update, name='col_update'),
    path('layout_age/', views.LayoutAgeView.as_view(), name='layout_age'),

    path('db/product/', views.ProductDatabaseView.as_view(), name='product_db'),
    path('db/storage/<str:pk>/', views.StorageDatabaseView.as_view(), name='storage_db'),
    path('db/product/json/', views.ProductDatabaseJson.as_view(), name='product_db_json'),
    path('db/storage/<str:pk>/json/', views.StorageDatabaseJson.as_view(), name='storage_db_json'),

    path('log/product/', views.ProductLogView.as_view(), name='product_log'),
    path('log/storage/', views.StorageLogView.as_view(), name='storage_log'),
    path('log/plan/', views.AgvProductionPlanLogView.as_view(), name='plan_log'),
    path('log/robot/', views.RobotQueueLogView.as_view(), name='robot_log'),
    path('log/queue/', views.AgvQueueLogView.as_view(), name='queue_log'),
    path('log/transfer/<slug:pk>/', views.AgvTransferLogView.as_view(), name='transfer_log'),
    path('log/product/json/', views.ProductLogJson.as_view(), name='product_log_json'),
    path('log/storage/json/', views.StorageLogJson.as_view(), name='storage_log_json'),
    path('log/plan/json/', views.AgvProductionPlanLogJson.as_view(), name='plan_log_json'),
    path('log/robot/json/', views.RobotQueueLogJson.as_view(), name='robot_log_json'),
    path('log/queue/json/', views.AgvQueueLogJson.as_view(), name='queue_log_json'),
    path('log/transfer/<slug:pk>/json/', views.AgvTransferLogJson.as_view(), name='transfer_log_json'),

    path('agv/', views.AgvListView.as_view(), name='agv'),
    path('agv/get_data_storage_form/', views.get_data_storage_form, name='get_data_storage_form'),
    path('agv/get_data_retrieval_form/', views.get_data_retrieval_form, name='get_data_retrieval_form'),
    path('agv/get_data_move_form/', views.get_data_move_form, name='get_data_move_form'),
    path('agv/get_data_agv_position/', views.get_data_agv_position, name='get_data_agv_position'),
    path('agv/plan_form/<slug:pk>/', views.PlanFormView.as_view(), name='plan_form'),
    path('agv/plan_form/<slug:pk>/plan_update/', views.plan_update, name='plan_update'),
    path('agv/plan_form/<slug:pk>/plan_delete/', views.plan_delete, name='plan_delete'),
    path('agv/plan_clear/', views.plan_clear, name='plan_clear'),
    path('agv/queue_form/<slug:pk>/', views.QueueFormView.as_view(), name='queue_form'),
    path('agv/queue_form/<slug:pk>/queue_update/', views.queue_update, name='queue_update'),
    path('agv/queue_form/<slug:pk>/queue_delete/', views.queue_delete, name='queue_delete'),
    path('agv/queue_clear/', views.queue_clear, name='queue_clear'),
    path('agv/robot_form/<slug:pk>/', views.RobotFormView.as_view(), name='robot_form'),
    path('agv/robot_form/<slug:pk>/robot_update/', views.robot_update, name='robot_update'),
    path('agv/robot_form/<slug:pk>/robot_delete/', views.robot_delete, name='robot_delete'),
    path('agv/robot_clear/', views.robot_clear, name='robot_clear'),
    path('agv/transfer_form/<slug:pk>/', views.TransferFormView.as_view(), name='transfer_form'),
    path('agv/transfer_form/<slug:pk>/transfer_update/', views.transfer_update, name='transfer_update'),

    path('agv_debug/', views.AgvTestListView.as_view(), name='agv_debug'),
    path('agv_debug/agv1_to_home', views.agv1_to_home, name='agv1_to_home'),

    path('graph_trend/', views.GraphTrendView.as_view(), name='graph_trend'),

]

sched.scheduler.start()
