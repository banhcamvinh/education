from django.urls import path,re_path
from django.urls.conf import include
from . import views

app_name = 'home'
urlpatterns = [
    path('',views.index, name= 'home'),
    path('login',views.login, name='login'),
    path('register',views.register, name='register'),
    path('forgotpass',views.forgotpass, name='forgotpass'),
    path('subscribe',views.subscribe, name='subscribe'),
    path('course',views.course, name='course'),
    re_path(r'^coursesearch',views.coursesearch, name='coursesearch'),
    path('course_overview/<int:id>',views.courseoverview,name='courseoverview'),
    path('cart', views.cart,name='cart'),
    path('pay/<str:code>', views.pay, name='pay'),
    path('course_learn/<int:id>', views.course_learn, name='course_learn'),
    path('course_certificate/<int:id>', views.course_certificate, name='course_certificate'),
    path('course_rating/<int:id>', views.course_rating, name='course_rating'),
    path('course_excercise/<int:id>/<str:lesson_name>', views.course_excercise, name='course_excercise'),
    path('user', views.user, name='user'),
    path('user_course', views.user_course, name='user_course'),
    path('user_account', views.user_account, name='user_account'),
    path('user_report', views.user_report, name='user_report'),
    path('admin', views.admin, name='admin'),
    path('admin_report', views.admin_report, name='admin_report'),
    path('teacher', views.teacher, name='teacher'),
    path('teacher_report', views.admin_report, name='teacher_report'),







    path('test',views.test, name='test'),
    path('ajax',views.ajax, name='ajax'),
    path('chat',views.chat, name='chat'),
]

