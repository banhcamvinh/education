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
    path('pay_pal/<str:code>', views.pay_pal, name='pay_pal'),
    path('paysuccess', views.paysuccess, name='paysucess'),
    path('course_learn/<int:id>', views.course_learn, name='course_learn'),
    path('course_certificate/<int:id>', views.course_certificate, name='course_certificate'),
    path('course_rating/<int:id>', views.course_rating, name='course_rating'),
    path('course_excercise/<int:id>/<str:lesson_name>', views.course_excercise, name='course_excercise'),
    path('user', views.user, name='user'),
    path('user_course', views.user_course, name='user_course'),
    path('user_account', views.user_account, name='user_account'),
    path('user_report', views.user_report, name='user_report'),
    path('user_register_teacher', views.user_register_teacher, name='user_register_teacher'),
    path('admin', views.admin, name='admin'),
    path('admin_report', views.admin_report, name='admin_report'),
    path('admin_teacher', views.admin_teacher, name='admin_teacher'),
    path('admin_user', views.admin_user, name='admin_user'),
    path('admin_course', views.admin_course, name='admin_course'),

    path('teacher', views.teacher, name='teacher'),
    path('teacher_report', views.teacher_report, name='teacher_report'),
    path('teacher_course', views.teacher_course, name='teacher_course'),
    path('teacher_part/<int:course_id>', views.teacher_part, name='teacher_part'),
    path('teacher_lesson/<int:course_id>/<str:part_name>', views.teacher_lesson, name='teacher_lesson'),
    path('teacher_exercise/<int:course_id>/<str:part_name>/<str:lesson_name>', views.teacher_exercise, name='teacher_exercise'),



    path('course_creation/<int:id>', views.course_creation, name='course_creation'),
    path('course_creation/<int:course_id>/part_creation/<str:part_name>', views.part_creation, name='part_creation'),
    path('course_creation/<int:course_id>/part_creation/<str:part_name>/lesson_creation/<str:lesson_name>', views.lesson_creation, name='lesson_creation'),
    path('course_creation/<int:course_id>/part_creation/<str:part_name>/lesson_creation/<str:lesson_name>/exercise_creation/<str:exercise_question>', views.exercise_creation, name='exercise_creation'),











    path('test',views.test, name='test'),
    path('ajax',views.ajax, name='ajax'),
    path('chat',views.chat, name='chat'),
]

