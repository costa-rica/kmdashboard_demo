from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app
from fileShareApp import db, bcrypt, mail
from fileShareApp.models import Post, User

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

#Kinetic Metrics, LLC
def userPermission(email):
    kmPermissions=['nickapeed@yahoo.com','test@test.com',
        'emily.reichard@kineticmetrics.com']
    if email in kmPermissions:
        return (True,'1,2,3,4,5,6,7,8')
    
    return (False,)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename) #splitext returns two values file name w/out ext, extension
#     f_name, f_ext = simply says put the first part in f_name and the second value in f_ext
# convention of an unused variable in coding is to use and "_". so this was f_name, but as Corey shared we're
# not using that variable
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    # app.root_path gives us full path up to our package directory. I think 'app' since well app is found
#    somewhere between run.py and __init__.py

    # code below uses Pillow (imported as PIL above) to resize the picture. Since the image will just be a small thumb
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='ricacbc@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, ignore email and there will be no change
'''
    mail.send(msg)


#return excel files formatted
def formatExcelHeader(workbook,worksheet, df, start_row):
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'align':'center',
        'border': 0})
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(start_row, col_num, value,header_format)
        width=len(value)+1 if len(value)>8 else 8
        worksheet.set_column(col_num,col_num,width)



def load_database_util(text_file_name, limit_upload_flag):
    #this util takes unzipped text file > converts to DF > appends to sqlite
    print('***in load_database_util***')
    if "inv" in text_file_name:
        col_names=['NHTSA_ACTION_NUMBER', 'MAKE','MODEL','YEAR','COMPNAME',
            'MFR_NAME','ODATE','CDATE','CAMPNO','SUBJECT',
          'SUMMARY']
        if limit_upload_flag:
            df_inv=pd.read_csv(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], text_file_name),
                sep='\t', lineterminator='\r', names=col_names,header=None,nrows=1000)
        else:
            df_inv=pd.read_csv(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], text_file_name),
                sep='\t', lineterminator='\r', names=col_names,header=None)
        df_inv['ODATE']=pd.to_datetime(df_inv['ODATE'],format='%Y%m%d')
        df_inv['CDATE']=pd.to_datetime(df_inv['CDATE'],format='%Y%m%d')
        df_inv['km_notes']=''
        df_inv['date_updated']=pd.to_datetime(datetime.now())
        df_inv['files']=''
        df_inv['categories']=''
        df_inv['linked_records']=''
        df_inv['source_file']=text_file_name
        df_inv['source_file_notes']=''
        df_inv['NHTSA_ACTION_NUMBER']=df_inv['NHTSA_ACTION_NUMBER'].map(lambda x: x.lstrip('\n'))
        try:
            df_inv.to_sql('investigations',db.engine, if_exists='append',index=False)
            return (f'Table successfully uploaded to database!', 'success')
        except:
            return (f"""Problem uploading: Check for 1)uniquness with id or RECORD_ID 2)date columns
                        are in a date format in excel.""",'warning')
    else:
        col_names=['RECORD_ID', 'CAMPNO', 'MAKETXT', 'MODELTXT', 'YEAR', 'MFGCAMPNO',
            'COMPNAME', 'MFGNAME', 'BGMAN', 'ENDMAN', 'RCLTYPECD', 'POTAFF',
            'ODATE', 'INFLUENCED_BY', 'MFGTXT', 'RCDATE', 'DATEA', 'RPNO', 'FMVSS',
            'DESC_DEFECT', 'CONSEQUENCE_DEFCT', 'CORRECTIVE_ACTION','NOTES',
            'RCL_CMPT_ID','MFR_COMP_NAME','MFR_COMP_DESC','MFR_COMP_PTNO']
        # df_re=pd.read_csv(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], text_file_name),
            # sep='\t', lineterminator='\r', names=col_names,header=None)
        if limit_upload_flag:
            df_re=pd.read_csv(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], text_file_name),
                names=col_names,header=None, sep='\t',nrows=1000)
        else:
            df_re=pd.read_csv(os.path.join(current_app.config['UPLOADED_TEMP_DATA'], text_file_name),
                names=col_names,header=None, sep='\t')
        df_re['YEAR']=df_re['YEAR'][:4]
        df_re['BGMAN']=df_re['BGMAN'][:9]
        df_re['ENDMAN']=df_re['ENDMAN'][:9]
        df_re['ODATE']=df_re['ODATE'][:9]
        df_re['RCDATE']=df_re['RCDATE'][:9]
        df_re['DATEA']=df_re['DATEA'][:9]
        df_re['BGMAN']=pd.to_datetime(df_re['BGMAN'],format='%Y-%m-%d')
        df_re['ENDMAN']=pd.to_datetime(df_re['ENDMAN'],format='%Y-%m-%d')
        df_re['ODATE']=pd.to_datetime(df_re['ODATE'],format='%Y-%m-%d')
        df_re['RCDATE']=pd.to_datetime(df_re['RCDATE'],format='%Y-%m-%d')
        df_re['DATEA']=pd.to_datetime(df_re['DATEA'],format='%Y-%m-%d')
        df_re['km_notes']=''
        df_re['date_updated']=pd.to_datetime(datetime.now())
        df_re['files']=''
        df_re['categories']=''
        df_re['linked_records']=''
        df_re['source_file']=text_file_name
        df_re['source_file_notes']=''
        try:
            df_re.to_sql('recalls',db.engine, if_exists='append',index=False)
            return (f'Table successfully uploaded to database!', 'success')
        except:
            return (f"""Problem uploading: Check for 1)uniquness with id or RECORD_ID 2)date columns
            are in a date format in excel.""",'warning')

def fix_recalls_wb_util(df_re,text_file_name):
        df_re['YEAR']=df_re['YEAR'][:4]
        df_re['BGMAN']=df_re['BGMAN'][:9]
        df_re['ENDMAN']=df_re['ENDMAN'][:9]
        df_re['ODATE']=df_re['ODATE'][:9]
        df_re['RCDATE']=df_re['RCDATE'][:9]
        df_re['DATEA']=df_re['DATEA'][:9]
        df_re['BGMAN']=pd.to_datetime(df_re['BGMAN'],format='%Y/%m/%d')
        df_re['ENDMAN']=pd.to_datetime(df_re['ENDMAN'],format='%Y/%m/%d')
        df_re['ODATE']=pd.to_datetime(df_re['ODATE'],format='%Y/%m/%d')
        df_re['RCDATE']=pd.to_datetime(df_re['RCDATE'],format='%Y/%m/%d')
        df_re['DATEA']=pd.to_datetime(df_re['DATEA'],format='%Y/%m/%d')
        df_re['km_notes']=''
        df_re['date_updated']=pd.to_datetime(datetime.now())
        df_re['files']=''
        df_re['categories']=''
        df_re['linked_records']=''
        df_re['source_file']=text_file_name
        df_re['source_file_notes']=''
        return df_re

