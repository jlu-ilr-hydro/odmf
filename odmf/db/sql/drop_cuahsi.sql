alter table dataset
    drop column cv_valuetype;
alter table dataset
    drop column cv_datatype;
alter table dataset
    drop column datacollectionmethod;
alter table valuetype
    drop column cv_variable_name;
alter table valuetype
    drop column cv_general_category;
alter table valuetype
    drop column cv_sample_medium;
alter table valuetype
    drop column cv_speciation;
alter table valuetype
    drop column cv_unit;
drop table datacollectionmethod;