import urllib
import pyrebase

#setting up firebase
firebaseConfig={
    "apiKey": "AIzaSyBOHxmgm-uhY4tQbK8YLLdNpP4IJYcHMrs",
    "authDomain": "education-5dcf4.firebaseapp.com",
    "databaseURL": "https://console.firebase.google.com/project/education-5dcf4/storage/education-5dcf4.appspot.com/files",
    "projectId": "education-5dcf4",
    "storageBucket": "education-5dcf4.appspot.com",
    "messagingSenderId": "398241938841",
    "appId": "1:398241938841:web:a88f98d2225e6a502d2708",
    "measurementId": "G-TBTMG79H88"
}

firebase=pyrebase.initialize_app(firebaseConfig)

#define storage
storage=firebase.storage()

print("success")

# Thêm video
# storage.child("test").put("test.mp4")

# Sử dụng cùng tên để update video

# Get url video
# url = storage.child("test.mp4").get_url(None)
# print(url)

# Xóa thì cứ đẩy file vào empty
# storage.child("empty").put("empty")
