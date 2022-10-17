# AWS Lambda / Google Sheets Integration

This Lambda function seeks to do three things:-

1. Create a Google Sheet and share it with a default editor
2. Count the number of non-null rows within the sheet
3. Share a read-only copy of the Sheet with another reader

It contains four functions besides the lambda handler:-

1. `authenticate()`
   1. This takes the various credentials from environment variables, and b64 decodes the private key as linebreaks cause issues
   2. It returns a `credentials` object -- with limited scope -- that can be used for other parts of the auth
2. `create_sheet()`
   1. This creates a new sheet, gives it a default editor, and returns the sheet identifier
3. `adjust_role()`
   1. This can technically adjust the role to anything else as the role is determined by a keyword argument.
   2. It is called by both `create_sheet` and by `lambda_handler`
4. `count_rows()`
   1. Returns the number of non-nullable rows in the sheet excluding the header row

### Sample payloads:

`Count rows`

```
{
  "attributes": {
    "spreadsheetId": "1CL8FYNeTpR_xIc9Lu72nOwJCEsaDl6pFxwSY26Dp0-g"
  },
  "action": "count_rows"
}
```

Successful response: 

```
{
  "statusCode": 200,
  "body": {
    "rowCount": 4
  }
}
```

`Create sheet`

```
{
  "attributes": {},
  "action": "create_sheet"
}
```

Successful response:

```
{
  "statusCode": 200,
  "body": {
    "spreadsheetId": "19NB1yma_ZrZP2DPIUR0rGCh8eW593q17A89Eemb61o8"
  }
}
```

`Add viewer`

```
{
  "attributes": {
    "spreadsheetId": "14xNON4PR6gkLWJTmcZovclSDLyzv3jHuyrLnoQ2S0i8",
    "emailAddress": "steven@sjohns.net"
  },
  "action": "add_viewer"
}
```

Successful response:

```
{
  "statusCode": 200
}
```

# Considerations

1. The private keys are kept in environment variables, however, this can move somewhere else to keep the keys reusable
2. By default, the initial email is shared with a single user. This can probably be adjusted so that it is shared with a group.
3. It uses the default Google API Python library which is *extremely* heavy. A better implementation would be to integrate the auth and the interactions yourself.