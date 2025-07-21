# Import the required module from the fyers_apiv3 package
from fyers_apiv3 import fyersModel

# Define your Fyers API credentials
client_id = "1STQ57NNRI-100"  # Replace with your client ID
secret_key = "HNVJE2C9WU"  # Replace with your secret key
redirect_uri = "https://google.com"  # Replace with your redirect URI
response_type = "code" 
grant_type = "authorization_code"  

# The authorization code received from Fyers after the user grants access
auth_code = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiIxU1RRNTdOTlJJIiwidXVpZCI6IjY0MzQ5MzhmYzRlYTRmNWZhNzJhYmMyMDE0OTZmMTc1IiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IkZBQjU1NTI4Iiwib21zIjoiSzEiLCJoc21fa2V5IjoiZWJlMTFmZDVmOWRlOGY4MDBiNWYyYTAyMzAzMDgxN2VlNmU0NmNhMTE3MWUxMmI2NjhlMGNkYzQiLCJpc0RkcGlFbmFibGVkIjoiTiIsImlzTXRmRW5hYmxlZCI6Ik4iLCJhdWQiOiJbXCJkOjFcIixcImQ6MlwiLFwieDowXCIsXCJ4OjFcIl0iLCJleHAiOjE3NTMxMDI2NDMsImlhdCI6MTc1MzA3MjY0MywiaXNzIjoiYXBpLmxvZ2luLmZ5ZXJzLmluIiwibmJmIjoxNzUzMDcyNjQzLCJzdWIiOiJhdXRoX2NvZGUifQ.vMKTzfnaXo409mFBa29YscIArpkxcr18vEqnNXAB6W8"

# Create a session object to handle the Fyers API authentication and token generation
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key, 
    redirect_uri=redirect_uri, 
    response_type=response_type, 
    grant_type=grant_type
)

# Set the authorization code in the session object
session.set_token(auth_code)

# Generate the access token using the authorization code
response = session.generate_token()

# Print the response, which should contain the access token and other details
print(response)

