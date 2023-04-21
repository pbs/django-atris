django-atris
============

Django-atris stores a snapshot of each tracked model on create/update/delete operations.

Snapshots are available in a global form as well.

This app requires:

- Django >= 1.10:
    - for Django < 1.9      please use django-atris < 1.0.0
    - for Django < 1.10     please use django-atris < 1.2.0
    - for Django > 2.0.0    please use django-atris > 1.2.1
    - for Django > 3.2      please use django-atris >= 2.0.1
- Postgresql
- Python:
    - for django-atris < 2.0.0  please use Python >= 2.7 or Python >= 3.4 (after Django 2)
    - for django-atris >= 2.0.0 please use Python >= 3.6

Integration guide
-----------------

In order to use the app you must do the following:

* Add 'atris' to INSTALLED_APPS in settings
* You MUST have 'django.contrib.postgres' in your INSTALLED_APPS
* Add 'atris.middleware.LoggingRequestMiddleware' to MIDDLEWARE in order for the app to be able to get the user which made the changes
* Put a field (named as you wish) in the model class that you desire to track that contains a HistoryLogging instance ( i.e. history = HistoryLogging() )

Additional features:

- Additional data -
                   if you wish to store some additional data regarding
                   an instance of your model, you can do so by adding a
                   dict to your model, which contains said additional data.
                   After creating that dict, use it when instantiating the
                   HistoryLogging field::

                        additional_data = {'changed_from': 'djadmin'}
                        history = HistoryLogging(additional_data_param_name='additional_data')

- Exclude fields -
                  if you wish not to track some fields, all you need to do
                  is add a list to your model which contains the fields you
                  do not wish to track in a string format and use that list
                  when instantiating the HistoryLogging field::

                       exclude_fields = ['last_modified'] # as it would always appear to have been updated
                       history = HistoryLogging(excluded_fields_param_name='exclude_fields')

- Ignore changes by user -
                  if you wish not to track changes made by a specific user,
                  such as a user specially set up for smoke tests, you can declare
                  an additional field called however you like and pass it on
                  to the HistoryLogging object. This field must be a dictionary
                  that contains the keys 'user_ids' and 'user_names', both values
                  for these keys must be lists containing the appropriate information::

                       ignore_history_for_users = {'user_ids': [1010101], 'user_names': ['ignore_user']}
                       history = HistoryLogging(ignore_history_for_users='ignore_history_for_users')

- Interested related fields -
                   **(added in version 1.1.0)**

                   if you wish to add history for the objects related to a model
                   when the model changes, you can do so by declaring a list with the names of
                   the related fields names. This is applicable to 1-to-1, 1-to-many and
                   many-to-many fields::

                      poll = ForeignKey('Poll')
                      ...
                      interested_related_fields = ['poll']
                      history = HistoryLogging(interested_related_fields='interested_related_fields')

Usage guide
-----------

After integrating the app in your own app, you can make use of it in several different ways.

For starters, the fields made available to you when inspecting a history instance are the following:

* content_type = django contenttype
* object_id = the model instance id that the history is kept of
* history_date = the date that the history instance was created
* history_user = the user that triggered the history instance (taken from middleware); For this string, the value it takes is prioritised in this order: fullname > email > username, if none are available it remains None.
* history_user_id = the id of the user that triggered the history instance (taken from middleware)
* history_type = type of history, +: Create, ~: Update, -:Delete (the method 'get_history_type_display()' gets you the string interpretation)
* data = JSON field, contains a snapshot (in the form of a dict) of the model instance that the history is being kept of, doesn't contain excluded fields nor additional data fields.
  All field values are converted to strings. The values of foreign keys are represented by the object ID as a string. The values of ManyToManyFields are represented by a string
  containing a comma-separated list of IDs.

    **New in version 1.1.0: changed key of ForeignKey fields from <FK_FIELD_NAME>_id to <FK_FIELD_NAME>; added entry for many-to-many field**
* additional_data = JSON field, contains additional data of the model instance in the form of a dict

**NOTE #1**: A historical record will be generated only if there has been a change in the local model fields. *(New in version 1.1.0)*

**NOTE #2**: You may implement your own `HistoricalRecord` class and specify it in your project's
settings.py via `ATRIS_HISTORY_MODEL` as `<APP_NAME>.<MODEL_NAME>`. *(New in version 1.1.0)*

Example of usage in code:

* Classes we will use in example::

    >>> class Foo(models.Model):
    ...   field_1 = models.CharField(max_length=255)
    ...   field_2 = models.IntField()
    ...   last_modified = models.DateTimeField(auto_now=True)
    ...   excluded_fields = ['last_modified']
    ...   ignore_history_for_users = {
    ...       'user_ids': [1010101],
    ...       'user_names': ['ignore_user'],
    ...   }
    ...   history = HistoryLogging(
    ...       excluded_fields='excluded_fields',
    ...       ignore_history_for_users='ignore_history_for_users,
    ...   )

    >>> class Bar(models.Model):
    ...   field_1 = models.CharField(max_length=255)
    ...   field_2 = models.IntField()
    ...   last_modified = models.DateTimeField(auto_now=True)
    ...   fk_field = models.ForeignKey(Foo)
          # setting this specifies the default value for your additional data
    ...   additional_data = {'modified_from': 'code'}
    ...   excluded_fields = ['last_modified']
    ...   interested_related_fields = ['fk_field']
    ...   history = HistoryLogging(
    ...       'additional_data',
    ...       'excluded_fields',
    ...       interested_related_fields='interested_related_fields',
    ...   )

    >>> foo = Foo.objects.create(field_1='aaa', field_2=0)
    >>> foo_1 = Foo.objects.create(field_1='bar', field_2=1)

* Get all the history information for the first model instance that was just created::

    >>> foo.history.all()
    [<HistoricalRecord: Create foo id=1>]

* Get all the history information for the Foo model::

    >>> Foo.history.all()
    [<HistoricalRecord: Create foo id=1>, <HistoricalRecord: Create foo id=2>]

* Get the global history information (ordered by history_date desc)::

    >>> from atris.models import HistoricalRecord
    >>> HistoricalRecord.objects.all()
    [<HistoricalRecord: Create bar id=1>, <HistoricalRecord: Create foo id=2>]

* Get all the history information for the Bar model::

    Bar.objects.create(field_1='aaa', field_2=0, fk_field=foo)
    >>> Bar.history.all()
    [<HistoricalRecord: Create bar id=1>]

* Get the global history information again::

    >>> HistoricalRecord.objects.all()
    [<HistoricalRecord: Update foo id=1>, <HistoricalRecord: Create bar id=1>,
      <HistoricalRecord: Create foo id=2>, <HistoricalRecord: Create foo id=1>]

  Note that an "update" historical record has been created for `foo` when a
  bar object was linked to it.

* Another way of getting history for a model::

    >>> HistoricalRecord.objects.by_model(Foo)
    [<HistoricalRecord: Update foo id=1>, <HistoricalRecord: Create foo id=1>,
     <HistoricalRecord: Create foo id=2>]

* Another way of getting history for an instance of a model useful for deleted objects that you still want a history for::

    >>> HistoricalRecord.objects.by_model_and_model_id(Foo, foo.id)
    [<HistoricalRecord: Update foo id=1>, <HistoricalRecord: Create foo id=1>]

* Get the snapshot of the bar instance created::

    >>> bar.history.first().data
    {'field_1': 'aaa', 'field_2': '0', 'fk_field': '1'}

* Get the additional data of the bar instance::

    >>> bar.history.first().additional_data
    {'modified_from': 'code'}

* If you have a situation where the user cannot be determined from the django middleware you can also do the following::

    >>> bar.history_user = User(username='username') # where User is the django User model
    >>> # Some other changes to bar so that a historical record will be generated.
    >>> bar.save()
    >>> bar.history.first().history_user
    'username'

* You can also mark a user such that the history for that user does not get saved. You can do so either by user name(KEEP IN MIND: user name is considered the full name or email or user name of the user instance associated with the history, depending on which is available first, in that order) or ID. You can use this to tell atris to ignore changes made by certain users such as a smoke test user::

    >>> bar.history_user = User(username='ignore_user') # where User is the django User model
    >>> bar.save()
    >>> bar.history.filter(history_user='ignore_user').count()
    0



Changelog
-----------

1.2.2:
    * Django 1.10 compatible

1.3.0:
    * Django 2 compatible

1.3.1:
    * suppress approximate count. TODO

1.3.2:
    * Django 2.1 compatible

1.3.3:
    * Evaluate translation lazy translation text for a field's verbose name

1.3.4:
    * Add support for Django 2.2

2.0.0:
    * Dropped support for Django < 2.2 and Python < 3.6
    * Fixed history generation issue after saving an instance for the first time after a new field was added to the model
        - This issue was causing historical records to be generated when saving (without any changes) existing instances of tracked models

2.0.1:
    * Dropping support for Python <= 3.6
    * Move away from setup.py to pyproject.toml
