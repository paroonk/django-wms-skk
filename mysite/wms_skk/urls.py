from django.urls import path

from . import views, sched

app_name = 'wms_skk'
urlpatterns = [
    path('', views.redirect_home, name='home'),
    path('permission_denied/', views.permission_denied, name='permission_denied'),
    path('auto_close', views.AutoCloseView.as_view(), name='auto_close'),

    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    path('layout/', views.LayoutView.as_view(), name='layout'),
    path('layout/<slug:pk>/inv_create/', views.inv_create, name='inv_create'),
    path('layout/<slug:pk>/inv_update/', views.inv_update, name='inv_update'),
    path('layout/<slug:pk>/inv_delete/', views.inv_delete, name='inv_delete'),

    path('product_db/', views.ProductDatabaseView.as_view(), name='product_db'),
    path('storage_db/', views.StorageDatabaseView.as_view(), name='storage_db'),

    path('product_log/', views.ProductLogView.as_view(), name='product_log'),
    path('storage_log/', views.StorageLogView.as_view(), name='storage_log'),
    path('plan_log/', views.AgvProductionPlanLogView.as_view(), name='plan_log'),
    path('robot_log/', views.RobotQueueLogView.as_view(), name='robot_log'),
    path('queue1_log/', views.AgvQueue1LogView.as_view(), name='queue1_log'),
    path('transfer1_log/', views.AgvTransfer1LogView.as_view(), name='transfer1_log'),

    path('agv/', views.AgvListView.as_view(), name='agv'),
    path('agv/get_data_storage_form/', views.get_data_storage_form, name='get_data_storage_form'),
    path('agv/get_data_retrieval_form/', views.get_data_retrieval_form, name='get_data_retrieval_form'),
    path('agv/get_data_move_form/', views.get_data_move_form, name='get_data_move_form'),
    path('agv/get_data_agv_position/', views.get_data_agv_position, name='get_data_agv_position'),
    path('agv/plan_form/<slug:pk>/', views.PlanFormView.as_view(), name='plan_form'),
    path('agv/plan_form/<slug:pk>/plan_update/', views.plan_update, name='plan_update'),
    path('agv/plan_form/<slug:pk>/plan_delete/', views.plan_delete, name='plan_delete'),
    path('agv/plan_clear/', views.plan_clear, name='plan_clear'),
    path('agv/queue1_form/<slug:pk>/', views.Queue1FormView.as_view(), name='queue1_form'),
    path('agv/queue1_form/<slug:pk>/queue1_update/', views.queue1_update, name='queue1_update'),
    path('agv/queue1_form/<slug:pk>/queue1_delete/', views.queue1_delete, name='queue1_delete'),
    path('agv/queue1_clear/', views.queue1_clear, name='queue1_clear'),
    path('agv/robot_form/<slug:pk>/', views.RobotFormView.as_view(), name='robot_form'),
    path('agv/robot_form/<slug:pk>/robot_update/', views.robot_update, name='robot_update'),
    path('agv/robot_form/<slug:pk>/robot_delete/', views.robot_delete, name='robot_delete'),
    path('agv/robot_clear/', views.robot_clear, name='robot_clear'),
    path('agv/transfer1_form/', views.Transfer1FormView.as_view(), name='transfer1_form'),
    path('agv/transfer1_form/transfer1_update/', views.transfer1_update, name='transfer1_update'),
    path('agv/transfer1_form/transfer1_delete/', views.transfer1_delete, name='transfer1_delete'),

    path('agv_debug/', views.AgvTestListView.as_view(), name='agv_debug'),
    path('agv_debug/agv1_to_home', views.agv1_to_home, name='agv1_to_home'),
]

# sched.scheduler.start()
