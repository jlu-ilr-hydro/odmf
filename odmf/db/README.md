# odmf.db

The odmf.db package handles the business logic / object relationship mapper of ODMF and relies on **SqlAlchemy 1.4.** 

All persistent objects are stored here. Internal dependencies are to be avoided - except from odmf.config and odmf.tools.Path 
Currently db.job depends on odmf.tools.mail

## Notes to developers

### New 
New data classes can easily be introduced. On each new start of the odmf-docker container, the command `odmf db-create`
is performed, which calls `odmf.tools.create_db.init_db()`. That function does a create_all call to the MetaData SQLAlchemy
ORM scheme. However, existing tables are not altered.
If you want to add a field to an existing dataclass, please extend the `odmf.tools.migrate_db.Migrate.run()` function
with the missing field. The add_field function will check if the field exists already and add it, if it is missing.


