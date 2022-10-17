from __future__ import print_function
import os
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account


SCOPES = {
    "sheets": ['https://www.googleapis.com/auth/spreadsheets'],
    "drive": ['https://www.googleapis.com/auth/drive.file']
}
CREDENTIAL_KEYS = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri',
                   'token_uri', 'auth_provider_x509_cert_url', 'client_x509_cert_url']


def authenticate(scopes):
    """
    Create the `credentials` object from the environment variables and tie it
    to scopes. This is used by all other functions that need to interact with
    Google.

    :param scopes:
    :return:
    """
    config = {}
    for key in CREDENTIAL_KEYS:
        # environment variables and \n don't go well together, so we b64 encode it
        # and decode it when needed
        if key == "private_key":
            config.update({key: base64.b64decode(os.environ[key])})
            continue
        config.update({key: os.environ[key]})

    credentials = service_account.Credentials.from_service_account_info(config, scopes=scopes)
    return credentials


def adjust_role(credentials, attributes, role="reader"):
    """
    Modify the roles of an existing Sheet. Takes an optional "role" parameter
    which can be used to specify any other role that might be expected, however,
    it is unlikely you will need to use this.

    :param credentials:
    :param attributes:
    :param role:
    :return:
    """
    try:
        drive_service = build('drive', 'v3', credentials=credentials)

        new_file_permission = {
            'type': 'group',
            'role': role,
            'emailAddress': attributes.get("emailAddress")  # let the api raise an error if empty
        }
        drive_service.permissions().create(
            fileId=attributes.get("spreadsheetId"), body=new_file_permission
        ).execute()
        return {"statusCode": 200}
    except HttpError as error:
        return {"statusCode": error.status_code, "body": error.reason}


def create_sheet(credentials, *args, **kwargs):
    """
    This function both creates a sheet and then assigns a default `editor` role to
    the Sheet. It takes no other parameters, the args and kwargs exist to keep the
    `lambda_handler` function cleaner/more consistent and capture an `attributes`

    :param credentials:
    :param args:
    :param kwargs:
    :return:
    """
    try:
        service = build('sheets', 'v4', credentials=credentials)
        spreadsheet = service.spreadsheets().create(fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        # set some email as the default editor, this could be set for a whole domain or role
        # or the email of a group, or perhaps the entire directory that this file is in can
        # be adjusted to something that may have already been shared granting immediate access
        params = {
            "spreadsheetId": spreadsheet_id,
            "emailAddress": os.environ.get("DEFAULT_EMAIL")
        }
        adjust_role(credentials, attributes=params, role="writer")

        return {"statusCode": 200, "body": {"spreadsheetId": spreadsheet_id}}
    except HttpError as error:
        return {"statusCode": error.status_code, "body": error.reason}


def count_rows(credentials, attributes):
    """
    Counts the non-null rows of a given document excluding the header. This acts exclusively
    on the first column, there *may* be some value in iterating across all the columns to see
    if they're empty too, or if there are other skippable values outside of null such as blank
    spaces or similar, but the assumption here is that we don't need to do that.

    :param credentials:
    :param attributes:
    :return:
    """
    try:
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=attributes.get("spreadsheetId"),
            range="A2:S"  # exclude headers
        ).execute()
        rows = result.get('values', [])

        # the below wont skip rows that, say, have just spaces or hypens or something.
        # the assumption is being made that this isn't expected, however, if we were
        # going to do this we can inspect it deeper and strip the columns or check to see
        # if they pass .isalnum() or similar.
        return {"statusCode": 200, "body": {"rowCount": len(list(filter(None, rows)))}}
    except HttpError as error:
        return {"statusCode": error.status_code, "body": error.reason}


def lambda_handler(event, context):
    """
    An `action` instructing this handler how to behave *must* be passed in
    or it will return a 400.

    :param event:
    :param context:
    :return:
    """
    if not event.get("action"):
        return {"statusCode": 400, "body": "No action provided to Lambda"}

    actions = {
        "add_viewer": [adjust_role, SCOPES["drive"]],
        "count_rows": [count_rows, SCOPES["sheets"]],
        "create_sheet": [create_sheet, SCOPES["sheets"]+SCOPES["drive"]],
    }

    action, credential_scope = actions[event["action"]]
    execution_outcome = action(
        credentials=authenticate(credential_scope),
        attributes=event["attributes"]
    )
    return execution_outcome
