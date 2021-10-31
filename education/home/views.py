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
from datetime import datetime

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Create your views here.
def index(request):
    myconnect = db.neo4j("bolt://localhost","neo4j","123")
    query = """
        call{
            match  (e:Enrollment)-[:to_course]->(c:Course)
            return c, count(*) as count
            order by count desc
            limit 3
        }
        with c
        MATCH (c:Course)
        OPTIONAL MATCH (c:Course)<-[:to_course]-(rc:Rating_Course)
        RETURN c.name as course_name, c.content as course_content ,coalesce(avg(rc.star),0)as course_rating
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
                //Course enrollmost
                //Course enrollmost
                //Course enrollmost
                match (c:Course)
                optional match (c:Course)-[tc:to_course]-(:Enrollment)
                with c, count(tc) as num_of_enrollment
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
                return course.id as id,course.name as name, apoc.agg.first(price)as price,num_of_enrollment,num_of_view, star
            """
            rs = myconnect.query(query)
            most_buy_course_lst = list(rs)
            most_buy_course_range = len(most_buy_course_lst) % 4
            most_buy_course_range = [*range(0,most_buy_course_range)]
            most_buy_course_render_lst = list(chunks(most_buy_course_lst,4))

            # Get course_lst view most
            query = """
                //Course views most
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
            most_view_course_range = len(most_view_course_lst) % 4
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
    
    context = {
        'cart_list':cart_list,
        'code':code,
        'codevalid':codevalid,
        'discount_price':discount_price,
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

def course_learn(request,id):
    # courseid 
    # part = ? lesson = ? excercise = ? 

    # Các part - đang học ở part nào
    # Các lesson - đang học ở chương nào
    # các notion trong lesson
    # If finish course -> open button to download certificate
    # Lesson nào xong thì tick
    # Edit note
    # Remove note
    # add note
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
        optional match (p)-[:head]-(:Lesson)-[:next*0..]->(l:Lesson)
        with p,l,c
        match (l)
        optional match (l)-[:head]-(:Exercise)-[:next*0..]->(e:Exercise)
        with p,l,coalesce(e.question,"") as q,coalesce(e.answer,"") as a,c
        with p,l,a,q,c
        match (l)
        optional match (:Account{{ username:'{}' }})-[:pay]-(e:Enrollment)-[:to_course]-(c),
        (e)-[:watching_lesson]-(wcl:Lesson)
        where (l)=(wcl)
        with p,l,a,q,count(wcl) as wcl
        with p,l,a,q,coalesce(wcl,"") as wcl
        return p.name as part_name,collect(l.name) as lesson_name,collect(l.url) as lesson_url,collect(q) as question_list,collect(a) as answer_list,collect(wcl) as watching
    """.format(id,username)
    rs = myconnect.query(query)
    course_learn_rs = list(rs)
    part_count = len(course_learn_rs)
    lesson_count = 0


    part_dict = {}
    for rc in course_learn_rs:
        lesson_dict = {}
        for index,lesson in enumerate(rc['lesson_name']):
            question = rc['question_list'][index]
            if lesson not in lesson_dict:
                # nếu bài học chưa có thì add vào dict
                lesson_dict[lesson] = []
            lesson_dict[lesson].append(question)
                # nếu bài học có rồi thì bổ sung vào dict
        part_dict[rc['part_name']] = lesson_dict
    

    for part,part_detail in part_dict.items():
        print(part)
        for lesson,lesson_detail in part_detail.items():
            print(lesson)
            print(lesson_detail)
        print()





    # part_dict = dict()
    # for rc in course_learn_rs:
    #     lesson_list = []
    #     for index,el in enumerate(rc['lesson_name']):
    #         if el not in lesson_list:
    #             lesson_list.append(el)

    #     part_dict[rc['part_name']] = lesson_list
    

            

        
        # part_dict sẽ add list lesson dict
        # lessondict sẽ có list 


 





    context = {
        'course_learn_all':course_learn_rs
    }
    template = loader.get_template('home/course_learn.html')
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