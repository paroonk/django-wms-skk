from django.urls import include, path
from rest_framework import routers

from . import sched, views

router = routers.DefaultRouter()
router.register('agvrobotstatus', views.AgvRobotStatusViewSet, basename='agvrobotstatus')
router.register('agvtransfer', views.AgvTransferViewSet, basename='agvtransfer')
router.register('agvproductionplan', views.AgvProductionPlanViewSet, basename='agvproductionplan')
router.register('robotqueue', views.RobotQueueViewSet, basename='robotqueue')
router.register('agvqueue', views.AgvQueueViewSet, basename='agvqueue')
router.register('product', views.ProductViewSet, basename='product')
router.register('storage/(?P<type>.*)', views.StorageViewSet, basename='storage')
router.register('productlog', views.ProductHistoryViewSet, basename='productlog')
router.register('storagelog', views.StorageHistoryViewSet, basename='storagelog')
router.register('agvproductionplanlog', views.AgvProductionPlanHistoryViewSet, basename='agvproductionplanlog')
router.register('robotqueuelog', views.RobotQueueHistoryViewSet, basename='robotqueuelog')
router.register('agvqueuelog', views.AgvQueueHistoryViewSet, basename='agvqueuelog')
router.register('agvtransferlog/(?P<id>[0-9]*)', views.AgvTransferHistoryViewSet, basename='agvtransferlog')
router.register('overviewgraph', views.OverviewGraphViewSet, basename='overviewgraph')
router.register('usagegraph', views.UsageGraphViewSet, basename='usagegraph')
router.register('historygraph', views.HistoryGraphViewSet, basename='historygraph')


app_name = 'wms'
urlpatterns = [
    path('', views.redirect_home, name='home'),
    path('api/', include(router.urls)),
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
    path('db/product/', views.ProductView.as_view(), name='db_product'),
    path('db/storage/<str:type>/', views.StorageView.as_view(), name='db_storage'),
    path('log/product/', views.ProductHistoryView.as_view(), name='log_product'),
    path('log/storage/', views.StorageHistoryView.as_view(), name='log_storage'),
    path('log/agvproductionplan/', views.AgvProductionPlanHistoryView.as_view(), name='log_agvproductionplan'),
    path('log/robotqueue/', views.RobotQueueHistoryView.as_view(), name='log_robotqueue'),
    path('log/agvqueue/', views.AgvQueueHistoryView.as_view(), name='log_agvqueue'),
    path('log/agvtransfer/<int:id>/', views.AgvTransferHistoryView.as_view(), name='log_agvtransfer'),
    path('historygraph/', views.HistoryGraphView.as_view(), name='historygraph'),
    path('agv/', views.AgvView.as_view(), name='agv'),
    path('agv/get_data_storage_form/', views.get_data_storage_form, name='get_data_storage_form'),
    path('agv/get_data_retrieval_form/', views.get_data_retrieval_form, name='get_data_retrieval_form'),
    path('agv/get_data_move_form/', views.get_data_move_form, name='get_data_move_form'),
    path('agv_debug/', views.AgvTestView.as_view(), name='agv_debug'),
    path('agv_debug/<int:pk>/agv_to_home', views.agv_to_home, name='agv_to_home'),
    path('agv/agvproductionplan_form/<slug:pk>/', views.AgvProductionPlanView.as_view(), name='agvproductionplan_form'),
    path('agv/agvproductionplan_form/<slug:pk>/agvproductionplan_update/', views.agvproductionplan_update, name='agvproductionplan_update'),
    path('agv/agvproductionplan_form/<slug:pk>/agvproductionplan_delete/', views.agvproductionplan_delete, name='agvproductionplan_delete'),
    path('agv/agvproductionplan_clear/', views.agvproductionplan_clear, name='agvproductionplan_clear'),
    path('agv/agvqueue_form/<slug:pk>/', views.AgvQueueView.as_view(), name='agvqueue_form'),
    path('agv/agvqueue_form/<slug:pk>/agvqueue_update/', views.agvqueue_update, name='agvqueue_update'),
    path('agv/agvqueue_form/<slug:pk>/agvqueue_delete/', views.agvqueue_delete, name='agvqueue_delete'),
    path('agv/agvqueue_clear/', views.agvqueue_clear, name='agvqueue_clear'),
    path('agv/robotqueue_form/<slug:pk>/', views.RobotQueueView.as_view(), name='robotqueue_form'),
    path('agv/robotqueue_form/<slug:pk>/robotqueue_update/', views.robotqueue_update, name='robotqueue_update'),
    path('agv/robotqueue_form/<slug:pk>/robotqueue_delete/', views.robotqueue_delete, name='robotqueue_delete'),
    path('agv/robotqueue_clear/', views.robotqueue_clear, name='robotqueue_clear'),
    path('agv/agvtransfer_form/<slug:pk>/', views.AgvTransferView.as_view(), name='agvtransfer_form'),
    path('agv/agvtransfer_form/<slug:pk>/agvtransfer_update/', views.agvtransfer_update, name='agvtransfer_update'),
]

sched.scheduler.start()
