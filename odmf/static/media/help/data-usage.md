# !fa-user-shield Use of personal data

The ODMF software uses personal data only for functional reasons. The system is designed to facilitate research 
data management. To enable users to claim their copyrights and for correct scientific attribution, personal data must 
be collected. It is strictly forbidden to use personal data from the ODMF system to share personal data with third parties,
assess work performance or to use for academic grading.

## What kind of personal data is stored in ODMF?

### Personal information in the user profile

- The person page contains the personal information of the users, the username (readonly), the real name and email 
  address, the affiliation. Users with the "supervisor" privilege or higher are visible for all users, the information
  of other users might be accessible for other users.
- The ORCID number is an optional value.
- The comment section of a user can include additional personal information.
- The date and time of the last login is saved and used for automatic deactivation of users and eventually removal of
  user accounts.
- The password is transmitted to ODMF but only an encrypted version is saved using the algorithm bcrypt2 implemented by 
  the python library with the same name. The password can not be retrieved from the encrypted form according to current 
  knowledge. The ODMF system should always be used with the secure https protocol.

Users are allowed and encouraged to edit their personal information to adjust their needs for privacy. However, the username
and the last login date are not writeable for the user. For correct scientific attribution, please do not try to use 
pseudonyms only. If you wish your name and personal information to be removed from the database, please see below.

### Data connected with the user profile
Users are members of projects, owners of datasets, authors of log book entries, jobs, comments on jobs, messages. 
This connection is transparent and needed for attribution of data and actions. The file manager stores who created 
(and owns) a directory.

### IP Address
To protect the database from illegal access, the IP Address and username is stored for max 6 months. This information is only
accessible to the technical administrators of the site.

### Cookies
ODMF itself uses a cookie to identify a logged in user over several page views, the so called session cookie. Otherwise the user would need to login
after each link. The session cookie saves additionally if the user has consented to use google maps.
ODMF saves additional information in the users webbrowser in clear text in the local storage about filters, 
map view properties and the latest plot. This information can be safely deleted and is not transferred to any 
third party. Therefore no consent to store cookies is necessary.

## What personal data does ODMF exchange with external parties
The ODMF server does not send personal data to any external parties without consent. 

### Google Maps
ODMF uses the Google Maps API, after the user consents. The user's web browser retrieves map data directly from Google Maps using Google's Javascript
API. Google sets cookies and provides the map data according to their terms and services that can be viewed here:

https://policies.google.com/privacy

Google may use additional information, like your IP address and more data if you are logged in with your Google Account.
ODMF can not control this data exchange, it is the same as a visit on the Google Maps web app.

## How to delete personal information (right to be forgotten)

### Deleting the user profile without data ownership 
If you just had a user profile without any depending data, your user profile can be deleted on request by the site
admins or starting 2025 deleted automatically 1 year after the last log in. Jobs, messages, comments will be deleted or attributed
to an anonymous user.

### Deleting the user profile for users with data ownership
If you are data owner in the filemanager, owner of datasets or author of logbook entries, please inform the site admins what needs to happen
with your data. In most cases, the ownership of the data is transferred to the spokesperson of the project, the data belongs to.
If the data is to be deleted, the handling site admin will ask the project admin for permission. In both cases you will lose the
ability to be correctly attributed for your work. One year after your last login, you will receive an email, how to proceed
with your datasets, offering the options above.
