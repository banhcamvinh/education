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



    path('test',views.test, name='test'),
    path('ajax',views.ajax, name='ajax'),
    path('chat',views.chat, name='chat'),
]

