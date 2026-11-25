from django.urls import path
from apps.staff import views as v
from apps.staff import views_attendance as a

urlpatterns = [
    path("employees/", v.EmployeeListCreateView.as_view(), name="employee-list"),
    path("employees/<int:pk>/", v.EmployeeDetailView.as_view(), name="employee-detail"),
    path("employees/<int:pk>/link-user/", v.LinkUserView.as_view(), name="employee-link-user"),
    path("employees/<int:pk>/schedule/", a.ScheduleView.as_view(), name="employee-schedule"),
    path("employees/<int:pk>/set-pin/", a.SetPinView.as_view(), name="employee-set-pin"),
    path("schedule/bulk/", a.BulkScheduleView.as_view(), name="schedule-bulk"),
    path("attendance/", a.BoardView.as_view(), name="attendance-board"),
    path("attendance/report/", a.ReportView.as_view(), name="attendance-report"),
    path("attendance/punch/", a.PunchView.as_view(), name="attendance-punch"),
    path("attendance/kiosk/", a.KioskView.as_view(), name="attendance-kiosk"),
    path("attendance/mark/", a.MarkView.as_view(), name="attendance-mark"),
    path("attendance/<int:pk>/", a.RecordView.as_view(), name="attendance-record"),
    path("riders/", v.RiderListView.as_view(), name="rider-list"),
    path("riders/<int:pk>/ledger/", v.RiderLedgerView.as_view(), name="rider-ledger"),
    path("riders/<int:pk>/settle/", v.RiderSettleView.as_view(), name="rider-settle"),
    path("orders/<int:pk>/assign-rider/", v.AssignRiderView.as_view(), name="assign-rider"),
]
