# !fa-envelope Messenger

The messenger system informs users of events. **Messages** are sent to topics and users can subscribe to **topics**. If a 
message is sent, an email is sent to every user who subscribed to one of the topics of the message. The messages are
also saved in the system for future reference here: odmf:/message/ . 

## !fa-inbox Topics and !fa-envelope Messages

A topic can be created by all "full" users, and users can subscribe to a topic on the topic-page or at their
personal user page. After subscription, the user will receive all messages sent to that topic as an email. 
All messages can be seen and filtered by topic and other means at the mail icon.

While users can send messages on their own (odmf:/message/new ), other parts of the system can publish messages also.

## !fa-tasks Jobs

Jobs are for task planning. Create a new job to inform other users (and yourself!) of pending tasks like field work. Other
users are informed eg. to remove their installations when a field is plowed or they can organize transport. [See here for more information](job)

## !fa-bell Dataset-Alarms

You can create alarms for datasets (open the dataset and open the tab alarms). Here you can create an alarm if
the last data of a dataset has values below or above a threshold. The data is aggregated and the alarm is created
if the count, mean, min, max, sum or standard deviation of the data in that timespan is below or above of your threshold.

Eg A data collector with 10min interval is not sending data, you might want to be informed if the dataset did receive
less then 4 or fewer values in the last hour. Then create an alarm with 1h aggregation time, `count` as the 
aggregation function and below 4 as the threshold. Create a meaningful topic, eg. `site:1` if your data is coming from
site:1.

