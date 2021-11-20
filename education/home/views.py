from logging import currentframe
from django import template
from django.http import response
from django.http.response import HttpResponse
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, JsonResponse
import json
import db
import mymail
import mywit
import time as t
from datetime import timedelta
from datetime import datetime
from datetime import date
import math
import numpy as np
import pandas as pd
from underthesea import sentiment

def get_sentiment(input):
    result = sentiment(str(input))
    return result

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Create your views here.
def index(request):
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    query = """
        call{
        match  (c:Course)
        optional match (e:Enrollment)-[:to_course]->(c:Course)
        return c, count(e) as count
        order by count desc
        limit 3
        }
        with c
        MATCH (c:Course)
        OPTIONAL MATCH (c:Course)<-[:to_course]-(rc:Rating_Course)
        return c.name as course_name, c.content as course_content, coalesce(avg(rc.star),0)  as course_rating
    """
    rs = myconnect.query(query)
    course_info_lst = list(rs)
    context = {
        'course_info_lst':course_info_lst
    }
    template = loader.get_template('home/home.html')
    return HttpResponse(template.render(context,request))

def login(request):
    if request.method == 'GET':
        if 'username' in request.session :
            del request.session['username']
            del request.session['role']
            return redirect('/')
        return render(request,'home/login.html')
    elif request.method == 'POST':
        alert = ""
        username = request.POST.get("username","")
        password = request.POST.get("password","")
        if username == "" or password == "":
            alert = "Bạn cần nhập đầy đủ thông tin"
        else:
            # Check username
            myconnect = db.neo4j("bolt://localhost","neo4j","123")
            rs = myconnect.query(query="MATCH (a:Account) RETURN a.username AS username")
            names = [record["username"] for record in rs]
            if username not in names:
                alert = "Sai tên tài khoản hoặc mật khẩu"
            # Check password
            else:
                print("Dô else")
                query = """
                MATCH (a:Account {{username:'{}',password:'{}'}}),
                (a)-[:in_role]->(r:Role),
                (a)-[:in_status]->(s:Status)
                return a.username as username,r.value as role,s.value as status
                """.format(username,password)
                rs = myconnect.query(query)
                rs = list(rs)
                if len(rs) == 0:
                    alert = "Sai tên tài khoản hoặc mật khẩu"
                elif rs[0]['status'] == 'inactive':
                    alert = "Tài khoản bị vô hiệu hóa"
                else:
                    alert="success"
                    request.session['username'] = rs[0]['username']
                    request.session['role'] = rs[0]['role']
                    return redirect('/')
        return render(request,'home/login.html',{'alert':alert})

def register(request):
    if request.method == 'GET':
        return render(request,'home/register.html')
    elif request.method == 'POST':
        alert = ""
        username = request.POST.get("username","")      
        password = request.POST.get("password","")
        confirmPassword = request.POST.get("confirmPassword","")
        if username == "" or password == "" or confirmPassword == "":
            alert = "Bạn cần nhập đầy đủ thông tin"
        else:
           # Check username
            myconnect = db.neo4j("bolt://localhost","neo4j","123")
            rs = myconnect.query(query="MATCH (a:Account) RETURN a.username AS username")
            names = [record["username"] for record in rs]
            if username in names:
                alert = "Tài khoản đã được đăng ký ! hãy đăng nhập hoặc tạo tài khoản khác"
            # Check password
            else:
                if password != confirmPassword:
                    alert= "Mật khẩu chưa khớp"
                else:
                    myconnect = db.neo4j("bolt://localhost","neo4j","123")
                    query = """
                    create (a:Account{{username:'{}',password:'{}' }})
                    ,(c:Cart),(a)-[:has_cart]->(c)
                    create (u:User{{name:"",dob:"",phone:"",email:""}})
                    create (u)-[:has_account]->(a)
                    create (a)-[:in_role]->(:Role{{value:'user'}})
                    create (a)-[:in_status]->(:Status{{value:'active'}})
                    """.format(username,password)
                    rs = myconnect.query(query)
                    alert="success"
        return render(request,'home/register.html',{'alert':alert})

def forgotpass(request):
    if request.method == 'GET':
        return render(request,'home/forgotpass.html',)
    elif request.method == 'POST':
        alert = ""
        email = request.POST.get("email","")
        username = request.POST.get("username","")
        if email == "" or username == "":
            alert = "Nhập email và username"
        else:
            # Check username
            myconnect = db.neo4j("bolt://localhost","neo4j","123")
            rs = myconnect.query(query="MATCH (a:Account) RETURN a.username AS username")
            names = [record["username"] for record in rs]
            if username not in names:
                alert = "Username không đúng!"
            else:
                alert = "Kiểm tra email để nhận mật khẩu mới"
                try:
                    mymail.send_email(email,"Mật khẩu mới cho tài khoản của bạn","abcd")
                except:
                    alert="Tài khoản email không đúng hoặc hệ thống lỗi ! vui lòng thử lại"
        return render(request,'home/forgotpass.html',{'alert':alert})

def subscribe(request):
    if request.method == 'POST':
        email = request.POST.get("email","")
        try:
            mymail.send_email(email,"Đăng ký nhận tin thành công","")
        except:
            pass
    return redirect('/')

def course(request):
    if request.method == 'GET':
        if request.GET.get("searchbtn"):
            searchbar = request.GET.get("searchbar","")
            # search with key word
            return redirect('/coursesearch/?searchkey={}&page=1'.format(searchbar))  

        else:
            myconnect = db.neo4j("bolt://localhost","neo4j","123")
            # Get category order by course quantity and course enrollment quanttty
            query = """
            call{
                match (ca:Category)
                optional match (co:Course)-[:belong_category]-(ca:Category)
                optional match (e:Enrollment)-[:to_course]-(co:Course)-[:belong_category]-(ca:Category)
                return ca as category, count(distinct co)as num_of_course,count(e) as num_of_enrollment
                order by num_of_course desc, num_of_enrollment desc
            }
            return category.value as name
            """
            rs = myconnect.query(query)
            category_lst = list(rs)

            # Get course_lst buy most
            query = """
                match (c:Course)
                optional match (c:Course)-[tc:to_course]-(e:Enrollment)
                with c, count(e) as num_of_enrollment
                order by num_of_enrollment desc
                limit 12
                match (c)
                optional match (c)-[wc:watching_course]-(:Account)
                with c,num_of_enrollment, count(wc) as num_of_view
                match (c)
                optional match (c)-[:to_course]-(rc:Rating_Course)
                with c,num_of_enrollment,num_of_view, coalesce(avg(rc.star),0) as star
                match (c)
                optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
                with  c as course, cp.value as price,d.value as day,m.value as month,y.value as year,num_of_enrollment,num_of_view,star
                order by year desc,month desc,day desc
                with course.id as id,course.name as name, apoc.agg.first(price)as price,num_of_enrollment,num_of_view, star
                order by num_of_enrollment desc
                return  id, name, price,num_of_enrollment,num_of_view, star
            """
            rs = myconnect.query(query)
            most_buy_course_lst = list(rs)
            most_buy_course_range = (len(most_buy_course_lst)-1) // 4 + 1
            most_buy_course_range = [*range(0,most_buy_course_range)]
            most_buy_course_render_lst = list(chunks(most_buy_course_lst,4))

            # Get course_lst view most
            query = """
                match (c:Course)
                optional match (c:Course)<-[wc:watching_course]-(:Account)
                with c,count(wc)as num_of_view
                match (c)
                optional match (c)-[:to_course]-(rc:Rating_Course)
                with c,num_of_view, coalesce(avg(rc.star),0) as star
                match (c)
                optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
                with  c as course, cp.value as price,d.value as day,m.value as month,y.value as year,num_of_view,star
                order by year desc,month desc,day desc
                return course.id as id,course.name as name, apoc.agg.first(price)as price,num_of_view, star
                order by num_of_view desc
            """
            rs = myconnect.query(query)
            most_view_course_lst = list(rs)
            most_view_course_range = (len(most_view_course_lst)-1) // 4 + 1
            most_view_course_range = [*range(0,most_view_course_range)]
            most_view_course_render_lst = list(chunks(most_view_course_lst,4))

            continue_course_lst = []
            continue_course_render_lst=[]
            continue_course_range=[]
            # check if logged in -> return continue list and recommend list
            if 'username' in request.session :
                query = """
                //Course watching
                    match (c:Course)<-[:watching_course]-(:Account{{username:"{}"}})
                    with c
                    limit 12
                    match (c)
                    optional match (c)-[:to_course]-(rc:Rating_Course)
                    with c, coalesce(avg(rc.star),0) as star
                    match (c)-[wc:watching_course]-(:Account)
                    with c, count(wc) as num_of_view,star
                    optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
                    with  c as course, cp.value as price,d.value as day,m.value as month,y.value as year,star,num_of_view
                    order by year desc,month desc,day desc
                    return course.id as id,course.name as name, apoc.agg.first(price)as price, star,num_of_view
                """.format(request.session['username'])
                rs = myconnect.query(query)
                continue_course_lst = list(rs)
                continue_course_range = (len(continue_course_lst)-1) // 4 + 1
                continue_course_range = [*range(0,continue_course_range)]
                continue_course_render_lst = list(chunks(continue_course_lst,4))



            context = {
                'category_lst':category_lst,

                'most_buy_course_lst':most_buy_course_lst,
                'most_buy_course_render_lst':most_buy_course_render_lst,
                'most_buy_course_range':most_buy_course_range,

                'most_view_course_lst':most_view_course_lst,
                'most_view_course_render_lst':most_view_course_render_lst,
                'most_view_course_range':most_view_course_range,

                'continue_course_lst':continue_course_lst,
                'continue_course_render_lst':continue_course_render_lst,
                'continue_course_range':continue_course_range,
            }
            template = loader.get_template('home/course.html')
            return HttpResponse(template.render(context,request))

def coursesearch(request):
    if request.method == "GET":  
        searchkey = request.GET.get('searchkey',"")
        filter = request.GET.get('filter',"")
        price_checked_list = request.GET.getlist('price', [])
        rating = request.GET.get('rating', 0)
        category_checked_list = request.GET.getlist('category', [])
        category_value_list = []
        myconnect = db.neo4j("bolt://localhost","neo4j","123")
        # get category
        query = """
            match (c:Category)
            optional match (c:Category)-[bc:belong_category]-(:Course)
            with c.value as name,count(bc) as num_of_course
            order by num_of_course desc
            return name
        """
        rs = myconnect.query(query)
        category_value_list = [record["name"] for record in rs]
        # get level
        level_value_list = []
        level_checked_list = request.GET.getlist('level', [])
        query = """
            match (c:Level)
            optional match (c:Level)-[bl:belong_level]-(:Course)
            with c.value as name,count(bl) as num_of_course
            order by num_of_course desc
            return name
        """
        rs = myconnect.query(query)
        level_value_list = [record["name"] for record in rs]

        orderby = ""
        if filter == 'viewmost':
            orderby = "order by num_of_view desc"
        elif filter == 'enrollmost':
            orderby = "order by num_of_enrollment desc"
        elif filter == 'toprating':
            orderby = "order by star desc"
        elif filter == 'newest':
            orderby = "order by year desc, month desc, day desc"
        elif filter == 'cheapest':
            orderby = "order by price asc"

        condition = "where"
        condition += " toLower(course.name) contains toLower('{}')".format(searchkey)
        if len(price_checked_list) != 0 and len(price_checked_list) != 2:
            if price_checked_list[0] == 'Có phí':
                condition += " and price <> 0"
            else:
                condition += " and price = 0"
        if rating != 0:
            condition += ' and star >='+str(rating)
        if len(category_checked_list) != 0:
            condition += ' and ('
            temp = ''
            for el in category_checked_list:
                temp += " or '{}' in category".format(el)
            temp = temp.replace("or","",1)
            temp += ')'
            condition += temp
        if len(level_checked_list) != 0 and len(level_checked_list) != len(level_value_list):
            condition += ' and ('
            temp = ''
            for el in level_checked_list:
                temp += " or level = '{}'".format(el)
            temp = temp.replace("or","",1)
            temp += ')'
            condition += temp



        query_for_count = """
            match (c:Course)
            optional match (c:Course)-[tc:to_course]-(:Enrollment)
            with c, count(tc) as num_of_enrollment
            match (c)
            optional match (c)-[wc:watching_course]-(:Account)
            with c,num_of_enrollment, count(wc) as num_of_view
            match (c)
            optional match (c)-[:to_course]-(rc:Rating_Course)
            with c,num_of_enrollment,num_of_view, coalesce(avg(rc.star),0) as star
            match (c)
            optional match (c)-[:with_course]-(cc:Course_Creation)
            with cc,c,num_of_enrollment,num_of_view, star
            match (c)
            optional match (cc)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
            with c,coalesce(d.value,0) as day,coalesce(m.value,0)as month,coalesce(y.value,0)as year,num_of_enrollment,num_of_view,star
            match (c)
            optional match (c)-[:belong_category]-(ca:Category)
            with c,day, month, year,num_of_enrollment,num_of_view,star,collect(ca.value)as category
            match(c)
            optional match (c)-[:belong_level]-(lv:Level)
            with c,day, month, year,num_of_enrollment,num_of_view,star,category,lv.value as level
            match (c)
            optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(pd:Day)<-[:in_day]-(pm:Month)-[:in_month]-(py:Year)
            with  c as course, coalesce(cp.value,0) as price,pd.value as pday,pm.value as pmonth,py.value as pyear,num_of_enrollment,num_of_view,star,day, month, year,category,level
            order by pyear desc,pmonth desc,pday desc
            {}
            with course.id as id,course.name as name, apoc.agg.first(price)as price,num_of_enrollment,num_of_view, star,day,month,year,category,level
            return count(name) as count
        """.format(condition)
        rs = myconnect.query(query_for_count)
        count = list(rs)
        count = count[0]['count']

        # 1 123
        # 2 456
        pagination = ''
        page = 5
        cur_page = request.GET.get('page',1)
        pre_page = int(cur_page) - 1
        nex_page = int(cur_page) + 1
        if pre_page < 1:
            pre_page = 1
        if nex_page > page * (int(cur_page) - 1):
            nex_page = page * (int(cur_page) - 1)
        pagination += ' skip ' + str(page * (int(cur_page) - 1) )
        pagination += ' limit ' + str(page)

        query = """
            // filter course
            match (c:Course)
            optional match (c:Course)-[tc:to_course]-(:Enrollment)
            with c, count(tc) as num_of_enrollment
            match (c)
            optional match (c)-[wc:watching_course]-(:Account)
            with c,num_of_enrollment, count(wc) as num_of_view
            match (c)
            optional match (c)-[:to_course]-(rc:Rating_Course)
            with c,num_of_enrollment,num_of_view, coalesce(avg(rc.star),0) as star
            match (c)
            optional match (c)-[:with_course]-(cc:Course_Creation)
            with cc,c,num_of_enrollment,num_of_view, star
            match (c)
            optional match (cc)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
            with c,coalesce(d.value,0) as day,coalesce(m.value,0)as month,coalesce(y.value,0)as year,num_of_enrollment,num_of_view,star
            match (c)
            optional match (c)-[:belong_category]-(ca:Category)
            with c,day, month, year,num_of_enrollment,num_of_view,star,collect(ca.value)as category
            match(c)
            optional match (c)-[:belong_level]-(lv:Level)
            with c,day, month, year,num_of_enrollment,num_of_view,star,category,lv.value as level
            match (c)
            optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(pd:Day)<-[:in_day]-(pm:Month)-[:in_month]-(py:Year)
            with  c as course, coalesce(cp.value,0) as price,pd.value as pday,pm.value as pmonth,py.value as pyear,num_of_enrollment,num_of_view,star,day, month, year,category,level
            order by pyear desc,pmonth desc,pday desc
            {}
            return course.id as id,course.name as name,course.content as content, apoc.agg.first(price)as price,num_of_enrollment,num_of_view, star,day,month,year,category,level
            {}
            {}
        """.format(condition,orderby,pagination)
        rs = myconnect.query(query)
        course_list = list(rs)
        # for el in course_list:
        #     print(el)
    




    context = {
        'searchkey':searchkey,
        'price_value_list': ['Có phí','Không phí'],
        'price_checked_list':price_checked_list,
        'rating_value_list':[1,2,3,4],
        'rating_checked':int(rating),
        'filter_value_list':['viewmost','enrollmost','newest','toprating','cheapest'],
        'filter_checked':filter,
        'category_value_list':category_value_list,
        'category_checked_list':category_checked_list,
        'level_value_list':level_value_list,
        'level_checked_list':level_checked_list,
        'course_list':course_list,
        'count':count,
        'page_value_list':[*range(1,(count-1)//page + 2)],
        'cur_page':int(cur_page),
        'pre_page':pre_page,
        'nex_page':nex_page,
    }
    template = loader.get_template('home/course_search.html')
    return HttpResponse(template.render(context,request))

def courseoverview(request,id):
    if request.method == "GET":
        action = request.GET.get('action','')
        myconnect = db.neo4j("bolt://localhost","neo4j","123")

        if action:
            if 'username' not in request.session:
                return redirect('/login')

            username = request.session['username']
            if action == 'buy':
                print('buy')
            elif action == 'add_cart':
                query ="""
                    match (:Account{{username:'{}'}})-[:has_cart]-(ca:Cart),(co:Course{{id:{} }})
                    merge (ca)-[:has_course]-(co)
                """.format(username,id)
                myconnect.query(query)
            elif action == 'remove_cart':
                query ="""
                    match (:Account{{username:'{}'}})-[:has_cart]-(ca:Cart)-[hc:has_course]-(co:Course{{id:{} }})
                    delete hc
                """.format(username,id)
                myconnect.query(query)
            elif action == 'add_mark':
                query ="""
                    match (:Account{{username:'{}'}})-[:has_course_mark]-(cm:Course_Mark),(c:Course{{ id:{} }})
                    merge (cm)-[:with_course]-(c)
                """.format(username,id)
                myconnect.query(query)
            elif action == 'remove_mark':
                query ="""
                    match (:Account{{ username:'{}' }})-[:has_course_mark]-(cm:Course_Mark)-[wc:with_course]-(c:Course{{id:{} }})
                    delete wc
                """.format(username,id)
                myconnect.query(query)
            

        isbought = False
        isadded = False
        ismarked =  False

        if 'username' in request.session:
            username = request.session['username']
            # check đã mua khóa học này chưa
            # mua rồi thì hiện nút vào học
            # mua rồi thì cho phép đánh giá

            query = """
            match (c:Course{{id:{}}})-[:to_course]-(:Enrollment)-[p:pay]-(:Account{{username:"{}"}})
            return c
            """.format(id,username)
            rs = myconnect.query(query)
            if len(list(rs)) != 0:
                isbought = True


            query = """
                match (a:Account{{username:'{}'}})-[:has_cart]-(:Cart)-[:has_course]-(:Course{{ id:{} }})
                return a
            """.format(username,id)
            rs = myconnect.query(query)
            if len(list(rs)) != 0:
                isadded = True
            query = """
                match (a:Account{{username:'{}'}})-[:has_course_mark]-(:Course_Mark)-[:with_course]-(:Course{{ id:{} }})
                return a
            """.format(username,id)
            rs = myconnect.query(query)
            if len(list(rs)) != 0:
                ismarked = True

        # Get course info
        query = """ 
            match (c:Course{{ id:{} }})
            with (c)
            match (c)
            optional match (c)-[:has_introduce_video]-(iv:`Introduce Video`)
            with (c),coalesce(iv.url,'https://www.youtube.com/embed/QupuYcUFuI8') as iv
            match (c)
            optional match (c)-[wc:watching_course]-(:Account)
            with (c),(iv),count(wc) as views
            match (c)
            optional match (c)-[:to_course]-(rc:Rating_Course)
            with (c),(iv),views,coalesce((avg(rc.star)),0) as star
            match (c)
            optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
            , (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
            with (c),(iv),views,star, count(distinct p)as part,count(l)as lesson,sum(l.duration) as duration
            match (c)
            optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(pd:Day)<-[:in_day]-(pm:Month)-[:in_month]-(py:Year)
            with  c as course, coalesce(cp.value,0) as price,pd.value as pday,pm.value as pmonth,py.value as pyear,(c),(iv)as video ,views,star,part,lesson,duration/60 as duration
            order by pyear desc,pmonth desc,pday desc
            return course.id as id,course.name as name,course.content as content,course.course_goal as goal,course.requirements as requirements,
            apoc.agg.first(price)as price,video as url ,views,star,part,lesson,duration
        """.format(id)
        rs = myconnect.query(query)
        course_detail = None
        course_rs = list(rs)
        if len(course_rs) != 0:
            course_detail = course_rs[0]

        # Get course rating
        query = """
            match (c:Course{{ id:{} }})-[:to_course]-(rc:Rating_Course)-[:make_rating]-(a:Account),
            (rc)-[:at]-(d:Day)-[:in_day]-(m:Month)-[:in_month]-(y:Year)
            return a.username as username,rc.star as star,rc.content as content,rc.time as time,d.value as day,m.value as month ,y.value as year       
        """.format(id)
        rs = myconnect.query(query)
        rating_list = list(rs)

        
        rating_checked = request.GET.get('rating',0)
        if rating_checked != 0 :
            rating_list = [x for x in rating_list if int(x['star']) >= int(rating_checked)]

        # 5 comment -> page 
        page = 1
        cur_page = request.GET.get('page',1)
        pre_page = int(cur_page) - 1
        nex_page = int(cur_page) + 1
        if pre_page < 1:
            pre_page = 1
        if nex_page > (len(rating_list)-1) //page + 1:
            nex_page = (len(rating_list)-1) //page + 1
        
        skip = page * (int(cur_page) - 1)
        limit = page
        page_value_list = range( 1, (len(rating_list)-1)//page + 2 )

        rating_list = rating_list[skip:skip+limit]


    context = {
        'isbought':isbought,
        'course_detail':course_detail,
        'rating_list':rating_list,
        'rating_checked':rating_checked,
        'page_value_list': page_value_list,
        'cur_page':int(cur_page),
        'pre_page':pre_page,
        'nex_page':nex_page,
        'ismarked': ismarked,
        'isadded': isadded,
    }
    template = loader.get_template('home/course_overview.html')
    return HttpResponse(template.render(context,request))

def cart(request):
    if request.method == "GET":
        if 'username' not in request.session:
            return redirect('/login')
        else:
            username = request.session['username']
            myconnect = db.neo4j("bolt://localhost","neo4j","123")

            remove = request.GET.get('remove',None)
            if remove and remove != '':
                query ="""
                    match (:Account{{username:'{}'}})-[:has_cart]-(ca:Cart)-[hc:has_course]-(co:Course{{id:{} }})
                    delete hc
                """.format(username,remove)
                myconnect.query(query)

            mark = request.GET.get('mark',None)
            if mark and mark != '':
                query ="""
                    match (:Account{{username:'{}'}})-[:has_course_mark]-(cm:Course_Mark),(c:Course{{ id:{} }})
                    merge (cm)-[:with_course]-(c)
                """.format(username,mark)
                myconnect.query(query)

            unmark = request.GET.get('unmark',None)
            if unmark and unmark != '':
                query ="""
                    match (:Account{{ username:'{}' }})-[:has_course_mark]-(cm:Course_Mark)-[wc:with_course]-(c:Course{{id:{} }})
                    delete wc
                """.format(username,unmark)
                myconnect.query(query)
            
            codevalid =  False
            discount_price = 0
            code = request.GET.get('code',None)
            if code and code != '':
                query ="""
                    match (:Discount_Code{{value:'{}'}})-[:has_discount_price]-(p:Discount_Price)
                    return p.value as price
                """.format(code)
                rs = myconnect.query(query)
                price = list(rs)
                if len(price) != 0:
                    codevalid = True
                    discount_price = price[0]['price']
                
            # check mã code xem có trong hệ thống không
            # Nếu không thì báo lõi
            # có thì giảm giá 

            # Get cart_list
            query = """
                match (a:Account{{username:'{}'}})-[:has_cart]-(:Cart)-[:has_course]-(c:Course)
                with c,a
                match (c)
                optional match (c)-[:with_course]-(:Course_Mark)-[hcm:has_course_mark]-(a)
                with c,count(hcm) as ismark
                with c,ismark
                match (c)
                optional match (c)-[wc:watching_course]-(:Account)
                with c, count(wc) as num_of_view,ismark
                match (c)
                optional match (c)-[:to_course]-(rc:Rating_Course)
                with c,num_of_view, coalesce(avg(rc.star),0) as star,ismark
                match (c)
                optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
                with  c as course, cp.value as price,d.value as day,m.value as month,y.value as year,num_of_view,star,ismark
                order by year desc,month desc,day desc
                return course.id as id,course.name as name, apoc.agg.first(price)as price,num_of_view, star,ismark
            """.format(username)
            rs = myconnect.query(query)
            cart_list = list(rs)
            total_price = 0
            for el in cart_list:
                total_price += el['price']

    context = {
        'cart_list':cart_list,
        'code':code,
        'codevalid':codevalid,
        'discount_price':discount_price,
        'total_price': total_price,
    }
    template = loader.get_template('home/cart.html')
    return HttpResponse(template.render(context,request))

def pay(request,code):
    if 'username' not in request.session:
            return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")

    dt = datetime.today()
    year = dt.year
    month = dt.month
    day = dt.day

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    if code == 'nonecode':
        code = None

    print(year,month,day,current_time,code,username)
    query = """
        // Create payment
        merge (d:Day{{value:{} }})
        merge (m:Month{{ value:{} }})
        merge (d)<-[:in_day]-(m)
        merge (y:Year{{ value:{} }})
        merge (m)<-[:in_month]-(y)
        merge (y)<-[:in_year]-(:Time)
        with d,m,y
        match (a:Account{{ username:'{}' }})
        with d,m,y,a
        create (a)-[:pay]->(e:Enrollment{{ time:'{}' }})-[:at]->(d)
        with a,e
        match (a)-[:has_cart]-(:Cart)-[hc:has_course]-(c:Course)
        create (e)-[:to_course]->(c)
        delete hc
        with e
        match (dc:Discount_Code{{ value:'{}' }})
        create (e)-[:with_discount_code]->(dc)
    """.format(day,month,year,username,current_time,code)
    myconnect.query(query)
    print("Thanh toán thành công")

    return redirect('/')

@csrf_exempt
def course_learn(request,id):
    if request.method == 'POST':
        username = request.session['username']
        myconnect = db.neo4j("bolt://localhost","neo4j","123")
        data = json.load(request)
        finish_lesson_video = data.get('finish_lesson_video')
        is_final_lesson = data.get('is_final_lesson')
        if finish_lesson_video != None:
            # delete finish cũ
            query = """
                match (c:Course{{ id: {} }} )
                with (c)
                match (c)
                optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
                with p,c
                match (p)
                optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
                with p,l,c
                match (l)<-[fl:finish_lesson]-(e:Enrollment)-[:pay]-(a:Account{{ username:'{}'}})
                optional match (l)
                delete fl
            """.format(id,username)
            myconnect.query(query)
            # create finish mới
            query = """
                match (c:Course{{ id: {} }} )
                with (c)
                match (c)
                optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
                with p,c
                match (p)
                optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
                with p,l,c
                match (l)
                where l.name = '{}'
                with l,c
                match (:Account{{ username:'{}' }})-[:pay]-(e:Enrollment)-[:to_course]-(c)
                create (e)-[:finish_lesson]->(l)
            """.format(id,finish_lesson_video,username)
            # tạo finish course nếu xong
            myconnect.query(query)
            if is_final_lesson == 1:
                query = """
                    match (a:Account{{username: '{}'}}),(c:Course{{ id: {} }})
                    create (a)-[:finish_course]->(c)
                """.format(username,id)
                myconnect.query(query)


        if finish_lesson_video == None:
            time = data.get('time')
            if time != None:
                time = math.floor(data.get('time'))
            note = data.get('note')
            cur_lesson = data.get('cur_lesson')
            if note == '':
                query = """
                    match (c:Course{{ id: {} }} )
                    with (c)
                    match (c)
                    optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
                    with p,c
                    match (p)
                    optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
                    with p,l,c
                    match (cur_l{{ name:'{}' }})
                    where cur_l = l
                    with p,cur_l,c
                    match (a:Account{{ username:'{}' }})-[:create_notion]-(n:notion)-[:in_lesson]->(cur_l)
                    where n.time = {}
                    detach delete n
                """.format(id,cur_lesson,username,time)
                myconnect.query(query)
            elif note != '':
                query = """
                    match (c:Course{{ id: {} }} )
                    with (c)
                    match (c)
                    optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
                    with p,c
                    match (p)
                    optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
                    with p,l,c
                    match (cur_l{{ name:'{}'}})
                    where cur_l = l
                    with p,cur_l,c
                    merge (a:Account{{ username:'{}' }})-[:create_notion]-(n:notion{{ time:{} }})-[:in_lesson]- (cur_l)
                    on match
                    set n.content = '{}'
                    on create
                    set n.time = {},n.content='{}'
                """.format(id,cur_lesson,username,time,note,time,note)
                myconnect.query(query) 
               

    # Lesson nào xong thì tick
    if 'username' not in request.session:
        return redirect('/login')

    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")

    # check xem user có mua khóa học này chưa chưa mua redirect qua overview
    query = """
        match (a:Account{{ username:'{}' }})-[:pay]-(:Enrollment)-[:to_course]-(c:Course{{ id:{} }})
        return count(a)
    """.format(username,id)
    rs = myconnect.query(query)
    if len(list(rs)) == 0:
        return redirect('/course_overview/{}'.format(id))

    # Đổ dữ liệu chung cho từng bài học
    query = """
        match (c:Course{{  id: {} }} )
        with (c)
        match (c)
        optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
        with p,c
        match (p)
        optional match (p)-[:head]-(ltest:Lesson)-[:next*0..]->(l:Lesson)
        with p,l,c
        match (l)
        optional match (l)-[:head]-(:Exercise)-[:next*0..]->(e:Exercise)
        with p,l,coalesce(e.question,"") as q,coalesce(e.answer,"") as a,c
        with p,l,a,q,c
        match (l)
        optional match (:Account{{ username:'{}' }})-[:pay]-(e:Enrollment)-[:to_course]-(c),
        (e)-[:finish_lesson]-(fnl:Lesson)
        where (l)=(fnl)
        with p,l,a,q,count(fnl) as fnl
        with p,l,a,q,coalesce(fnl,"") as fnl
        return p.name as part_name,collect(l.name) as lesson_name,collect(l.url) as lesson_url,collect(q) as question_list,collect(a) as answer_list,collect(fnl) as finish
    """.format(id,username)
    rs = myconnect.query(query)
    course_learn_rs = list(rs)
    part_count = len(course_learn_rs)
    lesson_count = 0

    part_dict = {}
    for rc in course_learn_rs:
        # convert query data to dict to return to template part dict -> lesson dict -> excercise list
        lesson_dict = {}
        for index,lesson in enumerate(rc['lesson_name']):
            question = rc['question_list'][index]
            finish = rc['finish'][index]
            if lesson not in lesson_dict:
                lesson_count += 1
                lesson_dict[lesson] = {}
                lesson_dict[lesson]['question_list'] = []
                lesson_dict[lesson]['finish_list'] = []
            if question != '':
                lesson_dict[lesson]['question_list'].append(question)
            lesson_dict[lesson]['finish_list'].append(finish)
        part_dict[rc['part_name']] = lesson_dict
    
    finish_part = 0
    finish_lesson = 0
    part_index = 0
    lesson_index = 0
    is_not_start = False
    check_finish_lesson_index = 0
    check_finish_lesson = 0
    cur_lesson_index = 0

    # how to get result
    for part,part_detail in part_dict.items():
        # print("Chương " + part)
        for lesson,lesson_detail in part_detail.items():
            # print("Bài " + lesson)
            # print(lesson_detail)
            for question in lesson_detail['question_list']:
                # print(question)
                pass
            for check in lesson_detail['finish_list']:
                if check == 1:
                    finish_lesson = lesson_index
                    finish_part = part_index
                    check_finish_lesson = check_finish_lesson_index
                # print(check)
            lesson_index += 1
            check_finish_lesson_index += 1
        check_finish_lesson_index = 0
        part_index +=1
        # print()
    

    # nếu trang là question thì sẽ vào question 
    # không phải thì vào trang lesson
    question = request.GET.get('question',None)
    if question == None:
        cur_lesson = request.GET.get('lesson',None)
        if cur_lesson is None:
            lesson_temp_index = 0
            last_dict = part_dict[(list(part_dict)[-1])]
            last_lesson = (list(last_dict)[-1])
            cur_lesson = last_lesson
            part_break = False
            for part,part_detail in part_dict.items():
                for lesson,lesson_detail in part_detail.items():
                    if finish_lesson == 0:
                        is_not_start = True
                        cur_lesson = lesson
                        part_break = True
                        break
                    if lesson_temp_index == finish_lesson + 1:
                        cur_lesson_index = lesson_temp_index
                        cur_lesson = lesson
                        part_break = True
                        break
                    lesson_temp_index += 1
                if part_break:
                    break
            context = {
                'auto_submit_lesson':True,
                'cur_lesson':cur_lesson
            }
            template = loader.get_template('home/course_learn.html')
            return HttpResponse(template.render(context,request))
        else:
            lesson_temp_index = 0
            part_break = False
            for part,part_detail in part_dict.items():
                for lesson,lesson_detail in part_detail.items():
                    if lesson == cur_lesson:
                        cur_lesson_index = lesson_temp_index
                        part_break = True
                        break
                    lesson_temp_index += 1
                if part_break:
                    break
            
        
    # check xem finish course chưa -> turn on certificate button
    is_finish_course = False
    query = """
        match (a:Account{{username:'{}'}})-[:finish_course]-(:Course{{id:{}}})
        return a
    """.format(username,id)
    rs = myconnect.query(query)
    if len(list(rs)) != 0:
        is_finish_course = True
    

    # Get note từ cur_lesson
    query = """
        match (c:Course{{ id: {} }} )
        with (c)
        match (c)
        optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
        with p,c
        match (p)
        optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
        with p,l,c
        match (a:Account{{ username:'{}' }})-[:create_notion]-(n:notion)-[:in_lesson]- (l2:Lesson{{name:'{}' }})
        where l2 = l
        return n.content as note, n.time as video_time
    """.format(id,username,cur_lesson)
    rs = myconnect.query(query)
    notion_list = []
    for el in list(rs):
        el_dict = dict()
        el_dict['video_time'] = el['video_time']
        el_dict['note'] = el['note']
        notion_list.append(el_dict)
    # Change note time về định dạng hh:mm:ss để hiển thị 
    for note in notion_list:
        note['video_time'] =t.strftime('%H:%M:%S', t.gmtime(note['video_time']))

    # Get watching time
    query = """
        match (c:Course{{ id:{} }} )
        with (c)
        match (c)
        optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
        with p,c
        match (p)
        optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
        with p,l,c
        match (cur_l{{ name:'{}' }})
        where cur_l = l
        with p,cur_l,c
        match (a:Account{{ username:'{}' }})-[:pay]->(e:Enrollment)-[wc:watching_lesson]-(cur_l)
        return wc.time as time
    """.format(id,cur_lesson,username)
    rs = myconnect.query(query)
    rs_list = list(rs)
    watching_time = 0
    if len(rs_list) != 0:
        watching_time = rs_list[0]['time']

    is_final_lesson = 0
    if cur_lesson_index == lesson_count - 1:
        is_final_lesson = 1
    # print(is_final_lesson)

    context = {
        'course_id': id,
        'part_dict': part_dict,
        'part_count': part_count ,
        'lesson_count':lesson_count,
        'finish_part':finish_part + 1,
        'finish_lesson':finish_lesson + 1,
        'is_not_start': is_not_start,
        'is_finish_course': is_finish_course,
        'notion_list': notion_list,
        'watching_time': watching_time,
        'cur_lesson':cur_lesson,
        'check_finish_lesson': check_finish_lesson + 1,
        'cur_lesson_index':cur_lesson_index + 1,
        'is_final_lesson':is_final_lesson,
    }
    template = loader.get_template('home/course_learn.html')
    return HttpResponse(template.render(context,request))

def course_certificate(request,id):
    # Check user đăng nhập hay chưa
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    # Check user hoàn thành khóa học hay chưa
    query = """
        match (a:Account{{username:'{}'}})-[:finish_course]-(c:Course{{id:{}}})
        return c.name as course_name
    """.format(username,id)
    rs = myconnect.query(query)
    rs_list = list(rs)
    if len(rs_list) == 0:
        return redirect('/course_learn/'+str(id))
    # Nếu đã hoàn thàn khóa học 
    course_name = rs_list[0]['course_name']

    context = {
        'username':username,
        'course_name': course_name,
    }
    template = loader.get_template('home/course_certificate.html')
    return HttpResponse(template.render(context,request))

def course_rating(request,id):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    star = request.GET.get('star','')
    content = request.GET.get('content','')
    is_success = False
    if star != '':
        query = """
            merge (a:Account{{username:'{}'}})-[:make_rating]-(rc:Rating_Course)-[:to_course]-(c:Course{{id:{} }})
            set rc.content = "{}"
            set rc.star = {}
        """.format(username,id,content,star)
        myconnect.query(query)
        is_success = True
    
    star = 0
    content = ''
    # Đã đánh giá hay chưa đánh giá rồi thì cho phép chỉnh sửa
    query = """
        match (a:Account{{username:'{}'}})-[:make_rating]-(rc:Rating_Course)-[:to_course]-(c:Course{{id:{}}})
        return rc.star as star, rc.content as content
    """.format(username,id)
    rs = myconnect.query(query)
    rs_list = list(rs)
    if rs_list != 0:
        star = rs_list[0]['star']
        content = rs_list[0]['content']

    context = {
        'star':star,
        'content':content,
        'star_loop':[1,2,3,4,5],
        'course_id':id,
        'is_success': is_success,
    }
    template = loader.get_template('home/course_rating.html')
    return HttpResponse(template.render(context,request))

def course_excercise(request,id,lesson_name):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    query = """
        match (c:Course{{ id: {} }} )
        with (c)
        match (c)
        optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
        with p,c
        match (p)
        optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
        with p,l,c
        match (l)
        where l.name = '{}'
        with l
        match (l)
        optional match (l)-[:head]-(:Exercise)-[:next*0..]->(e:Exercise)
        return e.question as question, e.answer as answer
    """.format(id,lesson_name)
    rs = myconnect.query(query)
    excercise_list = list(rs)

    context = {
        'excercise_list': excercise_list,
        'course_id':id,
    }
    template = loader.get_template('home/course_excercise.html')
    return HttpResponse(template.render(context,request))

def user(request):
    context = {
    }
    template = loader.get_template('home/user.html')
    return HttpResponse(template.render(context,request))

def user_register_teacher(request):
    alert = ""
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    is_registed = False
    if request.method == 'POST':
        query = """
            match (a:Account{{ username: '{}' }})
            merge (a)-[:has_teacher_register]-(:Teacher_Register)
        """.format(username)
        myconnect.query(query)
        is_registed = True
        alert = "Đăng kí thành công"
    else:
        query = """
            match (a:Account{{username:'{}'}})-[:has_teacher_register]-(:Teacher_Register)
            return *
        """.format(username)
        rs = myconnect.query(query)
        if len(list(rs)) != 0:
            is_registed = True

    context = {
        'alert':alert,
        'is_registed':is_registed,
    }
    template = loader.get_template('home/user_register_teacher.html')
    return HttpResponse(template.render(context,request))

def user_account(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    form_rs = None
    alert = ''
    if request.method == 'POST':
        name = request.POST.get("name","")
        phone = request.POST.get("phone","")
        email = request.POST.get("email","")
        rs_dict = dict()
        if name == "" or phone == "" or email == "":
            alert = "Bạn chưa điền đủ thông tin"
            form_rs = rs_dict
        else:
            alert = "Cập nhật thông tin thành công"
            query = """
                MATCH (a:Account {{username:'{}'}})<-[:has_account]-(u:User)
                set u.name = '{}' , u.phone = '{}' , u.email = '{}'
                return u.name as name, u.phone as phone, u.email as email
            """.format(username,name,phone,email)
            rs = myconnect.query(query)
            rs = list(rs)
            form_rs = rs[0]
                    
    if request.method == 'GET':
        query = """
            MATCH (a:Account {{username:'{}'}})<-[:has_account]-(u:User)
            return u.name as name, u.phone as phone, u.email as email
        """.format(username)
        rs = myconnect.query(query)
        rs = list(rs)
        form_rs = rs[0]
        print(type(form_rs))

    context = {
        'form_rs': form_rs,
        'alert':alert
    }
    template = loader.get_template('home/user_account.html')
    return HttpResponse(template.render(context,request))

def user_course(request):
    if request.method == 'GET':
        myconnect = db.neo4j("bolt://localhost","neo4j","123")

        continue_course_lst = []
        continue_course_render_lst=[]
        continue_course_range=[]
        # check if logged in -> return continue list and recommend list
        if 'username' in request.session :
            query = """
            //Course watching
                match (c:Course)<-[:watching_course]-(:Account{{username:"{}"}})
                with c
                match (c)
                optional match (c)-[:to_course]-(rc:Rating_Course)
                with c, coalesce(avg(rc.star),0) as star
                match (c)-[wc:watching_course]-(:Account)
                with c, count(wc) as num_of_view,star
                optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
                with  c as course, cp.value as price,d.value as day,m.value as month,y.value as year,star,num_of_view
                order by year desc,month desc,day desc
                return course.id as id,course.name as name, apoc.agg.first(price)as price, star,num_of_view
            """.format(request.session['username'])
            rs = myconnect.query(query)
            continue_course_lst = list(rs)
            continue_course_range = (len(continue_course_lst)-1) // 4 + 1
            continue_course_range = [*range(0,continue_course_range)]
            continue_course_render_lst = list(chunks(continue_course_lst,4))

            query = """
                match (a:Account{{ username:"{}" }})-[:has_course_mark]-(:Course_Mark)-[:with_course]-(c:Course)
                with c
                match (c)
                optional match (c)-[:to_course]-(rc:Rating_Course)
                with c, coalesce(avg(rc.star),0) as star
                match (c)
                optional match (c)-[wc:watching_course]-(:Account)
                with c, count(wc) as num_of_view,star
                optional match (c)-[:has_price]->(cp:Course_Price)-[:at]-(d:Day)<-[:in_day]-(m:Month)-[:in_month]-(y:Year)
                with  c as course, cp.value as price,d.value as day,m.value as month,y.value as year,star,num_of_view
                order by year desc,month desc,day desc
                return course.id as id,course.name as name, apoc.agg.first(price)as price, star,num_of_view
            """.format(request.session['username'])
            rs = myconnect.query(query)
            mark_course_lst = list(rs)
            mark_course_range = (len(mark_course_lst)-1) // 4 + 1
            mark_course_range = [*range(0,mark_course_range)]
            mark_course_render_lst = list(chunks(mark_course_lst,4))



        context = {
            'continue_course_lst':continue_course_lst,
            'continue_course_render_lst':continue_course_render_lst,
            'continue_course_range':continue_course_range,
            'mark_course_lst':mark_course_lst,
            'mark_course_render_lst':mark_course_render_lst,
            'mark_course_range':mark_course_range,
        }
        template = loader.get_template('home/user_course.html')
        return HttpResponse(template.render(context,request))

def user_report(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")

    # Finish course
    query = """
        match (a:Account{{username:'{}'}})
        optional match (a:Account{{username:'{}'}})-[:pay]-(e:Enrollment)-[:to_course]-(pc:Course)
        with count(pc) as total_course
        match (a:Account{{username:'{}'}})
        optional match (a:Account{{username:'{}'}})-[:pay]-(e:Enrollment)-[:finish_course]-(fnc:Course)
        return count(fnc) as finish, total_course - count(fnc) as not_finish
    """.format(username,username,username,username)
    rs = myconnect.query(query)
    finish_course = list(rs)
    if len(finish_course) != 0:
        finish_course = finish_course[0]
    
    # Finish lesson
    query = """
        match (:Account{{ username:'{}' }})-[:pay]-(e:Enrollment)-[:to_course]-(c)
        with (c)
        match (c)
        optional match (c)-[:head]-(:Part)-[:next*0..]->(p:Part)
        with p,c
        match (p)
        optional match (p)-[:head]-(ltest:Lesson)-[:next*0..]->(l:Lesson)
        with l,c
        match (l)
        optional match (:Account{{ username:'{}' }})-[:pay]-(e:Enrollment)-[:to_course]-(c),
        (e)-[:finish_lesson]-(fnl:Lesson)
        where (l)=(fnl)
        with l.name as l_name,l.duration as l_duration,fnl.name as fnl_name,c.name as course_name
        return *
    """.format(username,username)
    rs = myconnect.query(query)
    finish_lesson = None
    rs_list = list(rs)
    finish_duration =dict()
    finish_lesson = dict()

    if len(rs_list) != 0:
        finish_lesson['total'] = len(rs_list)
        finish_lesson['finish'] = 0
        finish_duration['finish'] = 0
        finish_duration['not_finish'] = 0
        finish_duration['total'] = 0
        course_dict = dict()

        for rs in rs_list:
            if rs['course_name'] not in course_dict:
                course_dict[rs['course_name']] = {'fnl_name':[], 'l_duration':[]}
            course_dict[rs['course_name']]['fnl_name'].append(rs['fnl_name'])
            course_dict[rs['course_name']]['l_duration'].append(rs['l_duration'])

        # print(course_dict)
        finish_index = 0
        for course in course_dict:
            count_none = 0
            for lesson in course_dict[course]['fnl_name']:
                count_none += 1
                lesson_index = course_dict[course]['fnl_name'].index(lesson)
                if lesson != None:
                    finish_lesson['finish'] += course_dict[course]['fnl_name'].index(lesson) + 1
                    finish_index = course_dict[course]['fnl_name'].index(lesson)
                finish_duration['total'] += course_dict[course]['l_duration'][lesson_index]
            if finish_index != 0:
                index = 0
                for lesson in course_dict[course]['l_duration']:
                    if index == finish_index + 1:
                        break
                    finish_duration['finish'] += lesson
                    index += 1
                finish_index = 0
            
        finish_lesson['not_finish'] = finish_lesson['total'] - finish_lesson['finish']
        finish_duration['not_finish'] = finish_duration['total'] - finish_duration['finish']

    context = {
        'finish_course':finish_course,
        'finish_lesson':finish_lesson,
        'finish_duration':finish_duration,
    }
    template = loader.get_template('home/user_report.html')
    return HttpResponse(template.render(context,request))

def admin(request):
    context = {
    }
    template = loader.get_template('home/admin.html')
    return HttpResponse(template.render(context,request))

def admin_report(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    # Get count rating
    star_dict = {
        '1':0,
        '2':0,
        '3':0,
        '4':0,
        '5':0,
        'mean':0,
        'p95':0,
    }
    query = """
        match (rc:Rating_Center)-[:at]-(d:Day)-[:in_day]-(m:Month)-[:in_month]-(y:Year)
        with rc.star as star, d.value as day, m.value as month, y.value as year
        return star
        order by year,month,day
    """.format()
    rs = myconnect.query(query)
    rs_list = list(rs)
    star_list = []
    for rs in rs_list:
        star_dict[str(rs['star'])] += 1
        star_list.append(rs['star'])
    star_dict['mean'] = ( star_dict['1'] + star_dict['2'] + star_dict['3'] + star_dict['4'] + star_dict['5'] ) / 5.0 
    star_dict['p95'] = np.quantile(star_list, 0.95)

    # Get view of all course
    query = """
        match (c:Course)
        optional match (c:Course)<-[wc:watching_course]-(a)
        return c.name as course_name, count(wc) as views 
    """.format()
    rs = myconnect.query(query)
    view_list = list(rs)

    # Get enroll of all course
    query = """
        match (c:Course)
    optional match (c:Course)<-[:to_course]-(e:Enrollment)
    return c.name as course_name, count(e) as enrollments
    """.format()
    rs = myconnect.query(query)
    enrollment_list = list(rs)

    # Get accout role by date
    query = """
        match (a:Account)-[:in_role]-(r:Role)
        where r.value <> "admin"
        with a,r.value as role
        match (a)-[:create_at]-(d:Day)-[:in_day]-(m:Month)-[:in_month]-(y:Year)
        return 
        sum(case role when "user" then 1 else 0 end) as user,
        sum(case role when "teacher" then 1 else 0 end) as teacher
        ,d.value as day, m.value - 1 as month, y.value as year
    """.format()
    rs = myconnect.query(query)
    role_list = list(rs)

    # Get rating content
    query = """
        match (rc:Rating_Center)-[:at]-(d:Day)-[:in_day]-(m:Month)-[:in_month]-(y:Year)
        return d.value as day, m.value as month, y.value as year, rc.content
        order by year,month,day
    """.format()
    rs = myconnect.query(query)
    rating_list = list(rs)
    rating_df = pd.DataFrame(rating_list,columns=['day','month','year','content'])
    rating_df['month'] = rating_df['month'].apply(lambda x:x)
    cols = ['year','month','day']
    rating_df['date'] = rating_df[cols].apply(lambda x: '-'.join(x.values.astype(str)), axis="columns")
    rating_df['date']= pd.to_datetime(rating_df['date'])
    rating_df['sentiment'] = rating_df['content'].apply(lambda x: get_sentiment(x))
    point_df = rating_df[['date','sentiment']]


    point_df = point_df.groupby('date')['sentiment'].apply(list).reset_index(name='sentiment')
    point_list = []
    date_list = point_df['date'].tolist()
    count_value_sentiment = 0
    count_positive = 0
    for index, row in point_df.iterrows():
        for sentiment in row['sentiment']:
            if sentiment != None:
                count_value_sentiment += 1
            if sentiment == 'positive':
                count_positive += 1
        point = count_positive / count_value_sentiment * 1.0 
        point *= 100
        point_list.append(point)
    
    sentiment_list = []
    for index,el in enumerate(date_list):
        sentiment_dict = dict()
        date_str = str(el)
        date_list = date_str.split(' ')
        date_list = date_list[0].split('-')
        sentiment_dict['day'] = date_list[2]
        sentiment_dict['month'] = date_list[1]
        sentiment_dict['year'] = date_list[0] 
        sentiment_dict['point'] = point_list[index]
        sentiment_list.append(sentiment_dict)

    print(star_dict)
    context = {
        'star_dict':star_dict,
        'view_list': view_list,
        'enrollment_list': enrollment_list,
        'role_list':role_list,
        'sentiment_list':sentiment_list
    }
    template = loader.get_template('home/admin_report.html')
    return HttpResponse(template.render(context,request))

def admin_teacher(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    register_list = list()
    teacher_list = list()
    if request.method == 'POST':
        approve_username = request.POST.get('approve','')
        remove_username = request.POST.get('remove','')
        if approve_username != '':
            query = """
                match (a:Account{{ username:'{}' }})-[hs:has_teacher_register]-(tr:Teacher_Register)
                delete hs, tr
                with a
                match (a)-[ir:in_role]-(r:Role)
                where r.value = 'user'
                delete ir
                with a
                match (r:Role)
                where r.value = 'teacher'
                with a,r
                create (a)-[:in_role]->(r)
            """.format(approve_username)
            myconnect.query(query)
        if remove_username != '':
            query = """
                match (a:Account{{ username:'{}' }})-[ir:in_role]-(r:Role)
                where r.value = 'teacher'
                delete ir
                with a
                match (r:Role)
                where r.value = 'user'
                with a, r
                create (a)-[:in_role]->(r)
            """.format(remove_username)
            myconnect.query(query)
            
    query = """
        match (a:Account)-[:has_teacher_register]-(:Teacher_Register),
        (a)-[:in_status]-(st:Status)
        where st.value = 'active'
        return a.username as username
    """.format()
    rs = myconnect.query(query)
    register_list = list(rs)
    # get teacher list
    query = """
        match (a:Account)-[:in_role]-(r:Role),
        (a)-[:in_status]-(s:Status)
        where r.value = 'teacher' and s.value = 'active'
        with a
        match (a)
        optional match (a)-[:create]-(cc:Course_Creation)
        return a.username as username,count(cc) as course
    """.format()
    rs = myconnect.query(query)
    teacher_list = list(rs)    

    context = {
        'teacher_list':teacher_list,
        'register_list':register_list,
    }
    template = loader.get_template('home/admin_teacher.html')
    return HttpResponse(template.render(context,request))

def admin_user(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    active_list = list()
    inactive_list = list()
    if request.method == 'POST':
        active_username = request.POST.get('active','')
        inactive_username = request.POST.get('inactive','')
        if active_username != '':
            query = """
                match (a:Account{{username:'{}'}})-[ir:in_role]-(r:Role),
                (a)-[is:in_status]-(s:Status)
                where r.value = 'user'
                delete is
                with a
                match (s:Status)
                where s.value = 'active'
                with a,s
                create (a)-[:in_status]->(s)
            """.format(active_username)
            myconnect.query(query)
        if inactive_username != '':
            print(inactive_username)
            query = """
                match (a:Account{{username:'{}'}})-[ir:in_role]-(r:Role),
                (a)-[is:in_status]-(s:Status)
                where r.value = 'user'
                delete is
                with a
                match (s:Status)
                where s.value = 'inactive'
                with a,s
                create (a)-[:in_status]->(s)
            """.format(inactive_username)
            myconnect.query(query)
            
    query = """
        match (a:Account)-[:in_role]-(r:Role),
        (a)-[:in_status]-(s:Status)
        where r.value = 'user' and s.value = 'active'
        return a.username as username
    """.format()
    rs = myconnect.query(query)
    active_list = list(rs)

    query = """
        match (a:Account)-[:in_role]-(r:Role),
        (a)-[:in_status]-(s:Status)
        where r.value = 'user' and s.value = 'inactive'
        return a.username as username
    """.format()
    rs = myconnect.query(query)
    inactive_list = list(rs)    

    context = {
        'active_list':active_list,
        'inactive_list':inactive_list,
    }
    template = loader.get_template('home/admin_user.html')
    return HttpResponse(template.render(context,request))

def admin_course(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    active_list = list()
    inactive_list = list()
    if request.method == 'POST':
        active_id = request.POST.get('active','')
        inactive_id = request.POST.get('inactive','')
        if active_id != '':
            query = """
                match (c:Course)-[in:in_status]-(s:Status)
                where s.value = 'inactive' and c.id = {}
                delete in
                with c
                match (s:Status)
                where s.value = 'active'
                with c,s
                create (c)-[:in_status]->(s)
            """.format(active_id)
            myconnect.query(query)
        if inactive_id != '':
            query = """
                match (c:Course)-[in:in_status]-(s:Status)
                where s.value = 'active' and c.id = {}
                delete in
                with c
                match (s:Status)
                where s.value = 'inactive'
                with c,s
                create (c)-[:in_status]->(s)
            """.format(inactive_id)
            myconnect.query(query)
            
    query = """
        match (c:Course)-[:in_status]-(s:Status)
        where s.value = 'active'
        return c.name as course_name, c.id as course_id
    """.format()
    rs = myconnect.query(query)
    active_list = list(rs)

    query = """
        match (c:Course)-[:in_status]-(s:Status)
        where s.value = 'inactive'
        return c.name as course_name, c.id as course_id
    """.format()
    rs = myconnect.query(query)
    inactive_list = list(rs)    

    context = {
        'active_list':active_list,
        'inactive_list':inactive_list,
    }
    template = loader.get_template('home/admin_course.html')
    return HttpResponse(template.render(context,request))


def teacher(request):
    context = {
    }
    template = loader.get_template('home/teacher.html')
    return HttpResponse(template.render(context,request))

def teacher_report(request):
    if 'username' not in request.session:
        return redirect('/login')
    username = request.session['username']
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    # Get count rating
    query = """
        match (a:Account{{username:'{}'}})-[:create]-(:Course_Creation)-[:with_course]-(c:Course) 
        with c
        match (c)
        optional match (c)-[:to_course]-(rc:Rating_Course)
        with c.name as course_name,rc.star as star
        return course_name,collect(star) as star_list,sum(star) as point
        order by point desc
        limit 5
    """.format(username)
    rs = myconnect.query(query)
    rs_list = list(rs)
    course_list = []
    for rs in rs_list:
        course_dict = dict()
        course_dict['name'] = rs['course_name']
        star_list = rs['star_list']
        star_dict = {
            '1':0,'2':0,'3':0,'4':0,'5':0
        }
        for star in star_list:
            star_dict[str(star)] += 1
        course_dict['star_dict'] = star_dict
        course_list.append(course_dict)

    query = """
        match (a:Account{{username:'{}'}})-[:create]-(:Course_Creation)-[:with_course]-(c:Course) 
        with c
        match (c)
        optional match (c)-[wc:watching_course]-(:Account)
        with c.name as course_name,count(wc) as views
        return *
        order by views desc
    """.format(username)
    rs = myconnect.query(query)
    view_list = list(rs)

    query = """
        match (a:Account{{username:'{}'}})-[:create]-(:Course_Creation)-[:with_course]-(c:Course) 
        with c
        match (c)
        optional match (c)-[:to_course]-(e:Enrollment)
        with c.name as course_name,count(e) as enrollments
        return *
        order by enrollments desc
    """.format(username)
    rs = myconnect.query(query)
    enrollment_list = list(rs)


    # Get rating content
    query = """
        match (a:Account{{username:'{}'}})-[:create]-(:Course_Creation)-[:with_course]-(c:Course) 
        with c
        match (c)
        optional match (c)-[:to_course]-(rc:Rating_Course)-[:at]-(d:Day)-[:in_day]-(m:Month)-[:in_month]-(y:Year)
        with c.name as course_name,rc.content as content,d.value as day, m.value as month, y.value as year
        return day,month,year,course_name,collect(content) as content
    """.format(username)
    rs = myconnect.query(query)
    rating_list = list(rs)
    rating_df = pd.DataFrame(rating_list,columns=['day','month','year','course_name','content'])
    rating_df['sentiment'] = rating_df['content'].apply(lambda x: get_sentiment(x))
    rating_df = rating_df[['sentiment','course_name']]
    rating_df = rating_df.groupby('course_name')['sentiment'].apply(list).reset_index(name='sentiment')
    sentiment_percentage_dict = dict()
    for index, row in rating_df.iterrows():
        value_sentiment_count = len(row['sentiment'])
        positive_sentiment_count = 0
        for el in row['sentiment']:
            if el == 'positive':
                positive_sentiment_count +=1
        sentiment_percentage = positive_sentiment_count / value_sentiment_count * 1.0
        sentiment_percentage_dict[row['course_name']] = sentiment_percentage

    context = {
        'course_list':course_list,
        'view_list':view_list,
        'enrollment_list':enrollment_list,
        'sentiment_percentage_dict':sentiment_percentage_dict,
    }
    template = loader.get_template('home/teacher_report.html')
    return HttpResponse(template.render(context,request))



def test(request):
    return render(request,'home/test.html',)



@csrf_exempt
def ajax(request):
    email = request.POST.get("email","")
    print(email)
    return HttpResponse(200)

@csrf_exempt
def chat(request):
    if request.method == 'GET':
        return render(request,'home/chat.html',)
    elif request.method == 'POST':
        data = json.load(request)
        in_message = data.get('payload')
        wit_res = mywit.client.message(in_message)
        out_mesasge = ""
        print(wit_res)
        if len(wit_res['intents']) == 0:
            out_mesasge = "Huhu chúng tớ chưa hiểu rõ câu hỏi mong bạn đặt lại câu hỏi hoặc nhờ hỗ trợ giúp mình nhé <3"
        elif wit_res['intents'][0]['name'] == 'Support' and wit_res['intents'][0]['confidence'] > 0.5:
            out_mesasge = """
            - Cần hỗ trợ gì bạn có thể nhắn lại tin nhắn + chủ đề đó
            - Cần hỗ trợ gấp bạn có thể gọi 113 hoặc gửi mail cho chúng tôi
            - Hoặc các bạn có thể liên lạc qua mạng xã hội
            """
        elif wit_res['intents'][0]['name'] == 'Course_Lifetime_Access' and wit_res['intents'][0]['confidence'] > 0.5:
            out_mesasge = """
            - Sau khi thanh toán bạn đã có thể vào học
            - Khóa học được sử dụng vô thời hạn
            - Bạn có thể sử dụng bất cứ đâu và bất cứ khi nào
            """
        elif wit_res['intents'][0]['name'] == 'Course_Price' and wit_res['intents'][0]['confidence'] > 0.5:
            out_mesasge = """
            - Các khóa học bao gồm có phí và miễn phí, sẽ được ghi cụ thể trên trang web
            """
        elif wit_res['intents'][0]['name'] == 'Course_info' and wit_res['intents'][0]['confidence'] > 0.5:
            out_mesasge = """
            - Các khóa học bao gồm video, các chương, bài học, bài tập mỗi bài và bài tập cuối khóa học
            - Bạn có thể sử dụng khóa học sau khi đã thanh toán
            - Khóa học sẽ cung cấp chứng chỉ sau khi học xong
            """
        elif wit_res['intents'][0]['name'] == 'Certificate' and wit_res['intents'][0]['confidence'] > 0.5:
            out_mesasge = """- Các khóa học bên mình đều cung cấp chứng chỉ sau khóa học.
            - Chứng chỉ sẽ được cung cấp sau khi bạn hoàn thành các khóa học.
            - Chứng chỉ có thể tải xuống để lưu trữ hoặc sử dụng với những mục đích theo ý bạn.
            - Chứng chỉ sẽ được in tên bạn.
            """
        elif wit_res['intents'][0]['name'] == 'Payment' and wit_res['intents'][0]['confidence'] > 0.5:
            out_mesasge = """-Hình thức thanh toán: thanh toán trực tiếp thông qua các phương thức có trên website
            - Gặp sự cố các bạn có thể liên hệ hỗ trợ
            """
        else:
            out_mesasge = "Huhu chúng tớ chưa hiểu rõ câu hỏi mong bạn đặt lại câu hỏi hoặc nhờ hỗ trợ giúp mình nhé <3"
        return JsonResponse({'message': out_mesasge})