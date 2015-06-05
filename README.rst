

django-atris
============

django-atris stores a snapshot of each tracked model on create/
update/delete operations.

Snapshots are available in a global form as well.

This app requires:
   - Django>=1.7
   - Postgresql
   - Python>=2.7

Integration guide
-----------------

In order to use the app you must do the following:
 * Add atris to INSTALLED_APPS in settings
 * Add 'atris.middleware.LoggingRequestMiddleware' to MIDDLEWARE_CLASSES in order for the app to be able to get the user which made the changes
 * Put a field (named as you wish) in the model class that you desire to track that contains a HistoryLogging instance (i.e. history = HistoryLogging() )

Additional features:
   - Additional data -
                       if you wish to store some additional data regarding
                       an instance of your model, you can do so by adding a
                       dict to your model, which contains said additional data.
                       After creating that dict, use it when instantiating the
                       HistoryLogging field.
                            additional_data = {'changed_from':'djadmin'}
                            history = HistoryLogging(additional_data)
   - Exclude fields -
                      if you wish to not track some fields, all you need to do
                      is add a list to your model which contains the fields you
                      do not wish to track in a string format and use that list
                      when instantiating the HistoryLogging field.
                           exclude_fields = ['last_modified'] # as it would always appear to have been updated
                           history = HistoryLogging(exclude_fields)

Usage guide
-----------

After integrating the app in your own app, you can make use of it in several different ways.

For starters, the fields made available to you when inspecting a history instance are the following:
    * content_type = django contenttype
    * object_id = the model instance id that the history is kept of
    * history_date = the date that the history instance was created
    * history_user = the user that triggered the history instance (taken from middleware)
    * history_user_id = the id of the user that triggered the history instance (taken from middleware)
    * history_type = type of history, +: Create, ~: Update, -:Delete (the method 'get_history_type_display()' gets you the string interpretation)
    * data = hstore field, contains a snapshot (in the form of a dict) of the model instance that the history is being kept of, doesn't contain excluded fields nor additional data fields
    * additional_data = hstore field, contains additional data of the model instance in the form of a dict

Example of usage in code:
* Classes we will use in example::

    >>> class Foo(models.Model):
    ...   field_1 = models.CharField(max_length=255)
    ...   field_2 = models.IntField()
    ...   last_modified = models.DateTimeField(auto_now=True)
    ...   excluded_fields = ['last_modified']
    ...   history = HistoryLogging(excluded_fields=excluded_fields)

    >>> class Bar(models.Model):
    ...   field_1 = models.CharField(max_length=255)
    ...   field_2 = models.IntField()
    ...   last_modified = models.DateTimeField(auto_now=True)
          # setting this specifies the default value for your additional data
    ...   additional_data = {'modified_from': 'code'}
    ...   excluded_fields = ['last_modified']
    ...   history = HistoryLogging(additional_data=additional_data,
    ...                            excluded_fields=excluded_fields)

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

    Bar.objects.create(field_1='aaa', field_2=0)
    >>> Bar.history.all()
    [<HistoricalRecord: Create bar id=1>]

* Get the global history information again::

    >>> HistoricalRecord.objects.all()
    [<HistoricalRecord: Create bar id=1>, <HistoricalRecord: Create foo id=2>,
     <HistoricalRecord: Create foo id=1>]

* Another way of getting history for a model::

    >>> HistoricalRecord.objects.by_model(Foo)
    [<HistoricalRecord: Create foo id=1>, <HistoricalRecord: Create foo id=2>]

* Another way of getting history for an instance of a model useful for deleted objects that you still want a history for::

    >>> HistoricalRecord.objects.by_model_and_model_id(Foo, foo.id)
    [<HistoricalRecord: Create foo id=1>]

* Get the snapshot of the bar instance created::

    >>> bar.history.first().data
    {u'field_1':u'aaa',u'field_2':u'0'}
* Get the additional data of the bar instance::

    >>> bar.history.first().additional_data
    {u'modified_from':u'code'}