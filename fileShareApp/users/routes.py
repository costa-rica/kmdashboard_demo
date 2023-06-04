from flask import Blueprint

from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app, send_from_directory
from fileShareApp import db, bcrypt, mail
from fileShareApp.models import User, Post, Investigations, Tracking_inv, \
    Saved_queries_inv, Recalls, Tracking_re, Saved_queries_re
from fileShareApp.users.forms import RegistrationForm, LoginForm, UpdateAccountForm, \
    RequestResetForm, ResetPasswordForm
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
from datetime import datetime, date, time
from sqlalchemy import func
import pandas as pd
import io
from wsgiref.util import FileWrapper
import xlsxwriter
from flask_mail import Message
from fileShareApp.users.utils import save_picture, send_reset_email, userPermission, \
    formatExcelHeader, load_database_util, fix_recalls_wb_util
import openpyxl
import json
import zipfile
from sqlalchemy import inspect

users = Blueprint('users', __name__)



@users.route("/home")
# @users.route("/", methods=["GET","POST"])
@login_required
def home():

    # try:
    #     if 'user' in inspect(db.engine).get_table_names():
    #         print("db already exists")
    # except:
    # #     Base.metadata.create_all(engine)
    #     # with app.app_context():
    #     db.create_all()
    #     print("NEW db created.")


    with open(os.path.join(current_app.config['UTILITY_FILES_FOLDER'],'added_users.txt')) as json_file:
        get_users_dict=json.load(json_file)
        json_file.close()
    allow_list=[i for i,j in get_users_dict.items() if j=='add privilege']
    return render_template('home.html', allow_list=allow_list)



@users.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    form= RegistrationForm()
    
    #Get list of emails allowed to register
    with open(os.path.join(current_app.config['UTILITY_FILES_FOLDER'],'added_users.txt')) as json_file:
        get_users=json.load(json_file)
        json_file.close()
    get_users_list=list(get_users.keys())
    
    if request.method == 'POST':
        if form.validate_on_submit():

            hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            if form.email.data in get_users_list:            
                user=User(email=form.email.data, password=hashed_password)
                db.session.add(user)
                db.session.commit()
                flash(f'You are now registered! You can login.', 'success')
            else:
                flash(f'You do not have permission to register', 'warning')
            return redirect(url_for('users.login'))
        else:
            flash(f'Did you mis type something? Check: 1) email is actually an email 2) password and confirm password match.', 'warning')
            return redirect(url_for('users.register'))
    return render_template('register.html', title='Register',form=form)

@users.route("/", methods=["GET","POST"])
@users.route("/login", methods=["GET","POST"])
def login():
    # print('***in login form****')
    print('request.args:::',request.args)
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    form = LoginForm()
    email_entry=request.args.get('email_entry')
    pass_entry=request.args.get('pass_entry')
    if request.args.get('email_entry'):
        form.email.data=request.args.get('email_entry')
        form.password_string.data=request.args.get('pass_entry')
        print('pass_entry:::', request.args.get('pass_entry'))
        
    if form.validate_on_submit():
        print('login - form.validate_on_submit worked')
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password_string.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('users.home'))
            #^^^ another good thing turnary condition ^^^
        else:
            flash('Login unsuccessful', 'danger')
    return render_template('login.html', title='Login', form=form)

    

@users.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('users.login'))



@users.route('/account', methods=["GET","POST"])
@login_required
def account():
    form=UpdateAccountForm()
    if form.validate_on_submit():
        # if form.picture.data:
            # picture_file = save_picture(form.picture.data)
            # current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        currentUser=User.query.get(current_user.id)
        currentUser.theme=request.form.get('darkTheme')
        db.session.commit()
        flash(f'Your account has been updated {current_user.email}!', 'success')
        return redirect(url_for('users.home')) #CS says want a new redirect due to "post-get-redirect pattern"
    #     post-get-redirect pattern is when browser asks are you sure you want to reload data.
    # It seems this is because the user will be running POst request on top of an existing post request
    elif request.method =='GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    #     This elif part is what i should do for preloading the DMR form with data when some already exists
    
    # if request.form.get('darkTheme'):
        # currentUser=User.query.get(current_user.id)
        # currentUser.theme='dark'
        # db.session.commit()
        
    # image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='account', form=form)


@users.route('/reset_password', methods = ["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('email has been sent with instructions to reset your password','info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', legend='Reset Password', form=form)

@users.route('/reset_password/<token>', methods = ["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Your password has been updated! You are now able to login', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', legend='Reset Password', form=form)




@users.route('/database_page', methods=["GET","POST"])
@login_required
def database_page():
    tableNamesList=['investigations','tracking_inv','recalls','tracking_re','user']
    # tableNamesList= db.engine.table_names()
    legend='Database downloads'
    if request.method == 'POST':
        formDict = request.form.to_dict()
        if formDict.get('build_workbook')=="True":
            
            #check if os.listdir(current_app.config['FILES_DATABASE']), if no create:
            if not os.path.exists(current_app.config['FILES_DATABASE']):
                # print('There is not database folder found???')
                os.mkdir(current_app.config['FILES_DATABASE'])
            
            for file in os.listdir(current_app.config['FILES_DATABASE']):
                os.remove(os.path.join(current_app.config['FILES_DATABASE'], file))

            
            timeStamp = datetime.now().strftime("%y%m%d_%H%M%S")
            workbook_name=f"database_tables{timeStamp}.xlsx"
            print('reportName:::', workbook_name)
            excelObj=pd.ExcelWriter(os.path.join(current_app.config['FILES_DATABASE'], workbook_name),
                date_format='yyyy/mm/dd', datetime_format='yyyy/mm/dd')
            workbook=excelObj.book
            
            dictKeyList=[i for i in list(formDict.keys()) if i in tableNamesList]
            dfDictionary={h : pd.read_sql_table(h, db.engine) for h in dictKeyList}
            for name, df in dfDictionary.items():
                if len(df)>900000:
                    flash(f'Too many rows in {name} table', 'warning')
                    return render_template('database.html',legend=legend, tableNamesList=tableNamesList)
                df.to_excel(excelObj,sheet_name=name, index=False)
                worksheet=excelObj.sheets[name]
                start_row=0
                formatExcelHeader(workbook,worksheet, df, start_row)
                print(name, ' table added to workbook')
                # if name=='dmrs':
                    # dmrDateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                    # worksheet.set_column(1,1, 15, dmrDateFormat)
                
            print('path of reports:::',os.path.join(current_app.config['FILES_DATABASE'],str(workbook_name)))
            excelObj.close()
            print('excel object close')
            # return send_from_directory(current_app.config['FILES_DATABASE'],workbook_name, as_attachment=True)
            return redirect(url_for('users.database_page'))
        elif formDict.get('download_db_workbook'):
            return redirect(url_for('users.download_db_workbook'))
        elif formDict.get('uploadFileButton'):
            print('****uploadFileButton****')
            formDict = request.form.to_dict()
            filesDict = request.files.to_dict()
            print('formDict:::',formDict)
            print('filesDict:::', filesDict)
            
            
            if not os.path.exists(current_app.config['UPLOADED_TEMP_DATA']):
                os.mkdir(current_app.config['UPLOADED_TEMP_DATA'])
            
            file_type=formDict.get('file_type')
            uploadData=request.files['fileUpload']
            uploadFileName=uploadData.filename
            uploadData.save(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], uploadFileName))
            if file_type=="excel":
                wb = openpyxl.load_workbook(uploadData)
                sheetNames=json.dumps(wb.sheetnames)
                tableNamesList=json.dumps(tableNamesList)

                return redirect(url_for('users.database_upload',legend=legend,tableNamesList=tableNamesList,
                    sheetNames=sheetNames, uploadFileName=uploadFileName,file_type=file_type))
            return redirect(url_for('users.database_upload',legend=legend,uploadFileName=uploadFileName,
                file_type=file_type))
            # return redirect(url_for('users.database_page'))
    return render_template('database_page.html', legend=legend, tableNamesList=tableNamesList)


@users.route("/download_db_workbook", methods=["GET","POST"])
@login_required
def download_db_workbook():
    # workbook_name=request.args.get('workbook_name')
    workbook_name = os.listdir(current_app.config['FILES_DATABASE'])[0]
    print('file:::', os.path.join(current_app.root_path, 'static','files_database'),workbook_name)
    file_path = r'D:\OneDrive\Documents\professional\20210610kmDashboard2.0\fileShareApp\static\files_database\\'
    
    return send_from_directory(os.path.join(current_app.config['FILES_DATABASE']),workbook_name, as_attachment=True)
    

@users.route('/database_delete_data', methods=["GET","POST"])
@login_required
def database_delete_data():
    legend='Clear Tables in Database'
    # dbModelsList= [cls for cls in db.Model._decl_class_registry.values() if isinstance(cls, type) and issubclass(cls, db.Model)]
    dbModelsList=[Investigations,Tracking_inv, Recalls, Tracking_re]
    # dbModelsDict={str(h)[22:-2]:h for h in dbModelsList}
    dbModelsDict={str(i)[28:-2]:i for i in dbModelsList}
    tableNameList=[h for h in dbModelsDict.keys()]
    if request.method == 'POST':
        formDict = request.form.to_dict()
        if formDict.get('removeData'):
            print('formDict::::',formDict)
            for tableName in formDict.keys():
                if tableName in tableNameList:
                    db.session.query(dbModelsDict[tableName]).delete()
                    db.session.commit()
            flash(f'Selected tables succesfully deleted', 'success')
    return render_template('database_delete_data.html', legend=legend, tableNameList=tableNameList)


@users.route('/database_upload', methods=["GET","POST"])
@login_required
def database_upload():
    file_type=request.args.get('file_type')
    if file_type=='excel':
        tableNamesList=json.loads(request.args['tableNamesList'])
        sheetNames=json.loads(request.args['sheetNames'])
    uploadFileName=request.args.get('uploadFileName')
    legend='Upload Data File to Database'
    # uploadFlag=True
    limit_upload_flag='checked'
    
    
    
    if request.method == 'POST':
        
        formDict = request.form.to_dict()
        print('formDict::::', formDict)
        if formDict.get('appendExcel'):
            
            uploaded_file=os.path.join(current_app.config['UPLOADED_TEMP_DATA'], uploadFileName)
            print('uploaded_file::::',uploaded_file)
            if file_type=='excel':
                for sheet in sheetNames:
                    sheetUpload=pd.read_excel(uploaded_file,engine='openpyxl',sheet_name=sheet)
                    if sheet=='user':
                        existing_emails=[i[0] for i in db.session.query(User.email).all()]
                        sheetUpload=pd.read_excel(uploaded_file,engine='openpyxl',sheet_name='user')
                        sheetUpload=sheetUpload[~sheetUpload['email'].isin(existing_emails)]

                    elif formDict.get(sheet) in ['investigations','recalls']:
                        sheetUpload['date_updated']=datetime.now()
                        if formDict.get(sheet) =='recalls':
                            sheetUpload=fix_recalls_wb_util(sheetUpload,uploadFileName)
                    try:
                        sheetUpload.to_sql(formDict.get(sheet),con=db.engine, if_exists='append', index=False)
                        print('upload SUCCESS!: ', sheet)
                    except IndexError:
                        pass
                    except:
                        os.remove(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], uploadFileName))

                        flash(f"""Problem uploading {sheet} table. Check for 1)uniquness with id or RECORD_ID 2)date columns
                            are in a date format in excel.""", 'warning')
                    
                    #clear files_temp folder
                    for file in os.listdir(current_app.config['UPLOADED_TEMP_DATA']):
                        os.remove(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], file))
                    flash(f'Table successfully uploaded to database!', 'success')
                    return redirect(url_for('users.database_page',legend=legend,
                        tableNamesList=tableNamesList, sheetNames=sheetNames))

                
            elif file_type=='text':
                zipfile.ZipFile(uploaded_file).extractall(path=current_app.config['UPLOADED_TEMP_DATA'])
                
                
                text_file_name=[x for x in os.listdir(current_app.config['UPLOADED_TEMP_DATA']) if x[-4:]=='.txt'][0]
                limit_upload_flag=formDict.get('limit_upload_flag')
                
                flash_message=load_database_util(text_file_name, limit_upload_flag)
                
                
                
                for file in os.listdir(current_app.config['UPLOADED_TEMP_DATA']):
                    os.remove(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], file))

                    
                flash(flash_message[0], flash_message[1])

                return redirect(url_for('users.database_page',legend=legend))

    
    if file_type=='excel':
        return render_template('database_upload.html',legend=legend,tableNamesList=tableNamesList,
                    sheetNames=sheetNames, uploadFileName=uploadFileName,
                    # uploadFlag=uploadFlag,
                    file_type=file_type)
    else:
        return render_template('database_upload.html',legend=legend,
                    uploadFileName=uploadFileName,
                    # uploadFlag=uploadFlag,
                    file_type=file_type,limit_upload_flag=limit_upload_flag)



@users.route("/admin", methods=["GET","POST"])
@login_required
def admin():
    users_list=[i.email for i in db.session.query(User).all()]
    
    with open(os.path.join(current_app.config['UTILITY_FILES_FOLDER'],'added_users.txt')) as json_file:
        get_users_dict=json.load(json_file)
        json_file.close()
    # get_users_list=list(get_users.keys())
    if request.method == 'POST':
        formDict = request.form.to_dict()
        print('formDict:::', formDict)
        if formDict.get('add_privilege'):
            
            get_users_dict[formDict.get('add_user')]='add privilege'
        else:
            get_users_dict[formDict.get('add_user')]='no add privileges'
        
        added_users_file=os.path.join(current_app.config['UTILITY_FILES_FOLDER'], 'added_users.txt')
        with open(added_users_file, 'w') as json_file:
            json.dump(get_users_dict, json_file)
        
        return redirect(url_for('users.admin'))
    return render_template('admin.html', users_list=get_users_dict)

@users.route("/delete_user/<email>", methods=["GET","POST"])
@login_required
def delete_user(email):
    print('did we get here????', email)
    with open(os.path.join(current_app.config['UTILITY_FILES_FOLDER'],'added_users.txt')) as json_file:
        get_users_dict=json.load(json_file)
        json_file.close()
    
    del get_users_dict[email]
    
    added_users_file=os.path.join(current_app.config['UTILITY_FILES_FOLDER'], 'added_users.txt')
    with open(added_users_file, 'w') as json_file:
        json.dump(get_users_dict, json_file)
        
    if len(db.session.query(User).filter_by(email=email).all())>0:
        db.session.query(User).filter_by(email=email).delete()
        db.session.commit()
    
    
    
    flash(f'{email} has been deleted!', 'success')
    return redirect(url_for('users.admin'))





