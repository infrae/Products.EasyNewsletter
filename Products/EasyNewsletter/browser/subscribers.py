import csv
import tempfile

from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements, Interface

from Products.EasyNewsletter import EasyNewsletterMessageFactory as _
from Products.EasyNewsletter.config import SALUTATION
from Products.EasyNewsletter.interfaces import ISubscriberSource
from Products.validation import validation


CSV_HEADER = [_(u"salutation"), _(u"fullname"), _(u"email"), _(u"organization"), ]


class IEnl_Subscribers_View(Interface):
    """
    Enl_Subscribers_View interface
    """


class Enl_Subscribers_View(BrowserView):
    """
    Enl_Subscribers_View browser view
    """
    implements(IEnl_Subscribers_View)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def portal_catalog(self):
        return getToolByName(self.context, 'portal_catalog')

    @property
    def portal(self):
        return getToolByName(self.context, 'portal_url').getPortalObject()

    def subscribers(self):
        subscribers = list()

        # Plone subscribers
        for brain in self.portal_catalog(portal_type = 'ENLSubscriber',
                                         path='/'.join(self.context.getPhysicalPath()),
                                         sort_on='email'):
            if brain.salutation:
                salutation = SALUTATION.getValue(brain.salutation, '')
            else:
                salutation = ''
            subscribers.append(dict(source='plone',
                               deletable=True,
                               email=brain.email,
                               getURL=brain.getURL(),
                               salutation=salutation,
                               fullname=brain.fullname,
                               organization=brain.organization))

        # External subscribers
        external_source_name = self.context.getSubscriberSource()
        if external_source_name != 'default':
            try:
                external_source = getUtility(ISubscriberSource, name=external_source_name)
            except ComponentLookupError:
                pass

            for subscriber in external_source.getSubscribers(self.context):
                subscriber['source'] = external_source_name
                subscribers.append(subscriber)

        return subscribers


def decode_string(string, encoding):
    if not isinstance(string, unicode):
        assert encoding is not None, 'API Error'
        string = string.decode(encoding)
    return string.strip()

def decode_list(values, encoding):
    return map(lambda v: decode_string(v, encoding), values)

def normalize_list(values, encoding):
    return map(lambda v: v.lower(), decode_list(values, encoding))


class UploadCSV(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def create_subscribers(self, csv_data=None):
        """Create newsletter subscribers from uploaded CSV file.
        """

        # Do nothing if no submit button was hit
        if 'form.button.Import' not in self.request.form:
            return

        context = aq_inner(self.context)
        lang = context.Language()
        plone_utils = getToolByName(context, 'plone_utils')
        encoding = plone_utils.getSiteEncoding()
        existing = set(context.objectIds())
        success = []
        fail = []
        data = []


        def error(msg):
            IStatusMessage(self.request).addStatusMessage(msg, type='error')
            return self.request.response.redirect(
                context.absolute_url() + '/@@upload_csv')

        # Show error if no file was specified
        filename = self.request.form.get('csv_upload', None)
        if not filename:
            return error(_('No file specified.'))

        # Detect the dialect of the CSV, and load it
        dialect = csv.Sniffer().sniff(filename.read())
        filename.seek(0)
        reader = csv.reader(filename, dialect=dialect)

        # Verify header
        header = normalize_list(reader.next(), encoding)
        expected_header = normalize_list(
            [context.translate(_(x)) for x in CSV_HEADER], None)
        if header != expected_header:
            return error(_("CSV file header doesn't match expected one."))

        for index, line in enumerate(reader):
            # Check the length of the line
            if len(line) != 4:
                msg =_('The number of entries on the line ${line} is not correct.',
                       mapping=dict(line=index))
                fail.append({'failure': msg})
                continue

            try:
                subscriber = decode_list(line, encoding)
            except UnicodeDecodeError:
                msg = _('The CSV file is not encoded in ${encoding}.',
                        mapping=dict(encoding=encoding))
                fail.append({'failure': msg})
                continue

            salutation = subscriber[0]
            fullname = subscriber[1]
            email = subscriber[2]
            organization = subscriber[3]

            if validation.validate('isEmail', email.encode('utf-8')) != 1:
                msg = _('This email is not a valid email address.')
                fail.append(
                    {'salutation': salutation,
                     'fullname': fullname,
                     'email': email,
                     'organization': organization,
                     'failure': msg})
                continue                
            identifier = plone_utils.normalizeString(email).lower()
            if identifier in existing:
                msg = _('This email address is already registered.')
                fail.append(
                    {'salutation': salutation,
                     'fullname': fullname,
                     'email': email,
                     'organization': organization,
                     'failure': msg})
                continue
            title = u" - ".join((email, fullname))
            try:
                context.invokeFactory('ENLSubscriber',
                    id=identifier,
                    title=title,
                    description="",
                    language=lang)
                obj = context._getOb(identifier)
                obj.email = email
                obj.fullname = fullname
                obj.organization = organization
                obj.salutation = salutation
                obj.reindexObject()
                existing.add(identifier)
                success.append(
                    {'salutation': salutation,
                     'fullname': fullname,
                     'email': email,
                     'organization': organization})
            except Exception, e:
                fail.append(
                    {'salutation': salutation,
                     'fullname': fullname,
                     'email': email,
                     'organization': organization,
                     'failure': 'An error occured while creating this subscriber: %s' % str(e)})

        return {'success': success, 'fail': fail}


class DownloadCSV(BrowserView):

    def __call__(self):
        """Returns a CSV file with all newsletter subscribers.
        """
        context = aq_inner(self.context)
        ctool = getToolByName(context, 'portal_catalog')

        # Create CSV file
        filename = tempfile.mktemp()
        file = open(filename, 'wb')
        csvWriter = csv.writer(file,
                               delimiter=',',
                               quotechar='"',
                               quoting=csv.QUOTE_MINIMAL)
        CSV_HEADER_I18N = [self.context.translate(_(x)) for x in CSV_HEADER]
        csvWriter.writerow(CSV_HEADER_I18N)
        for subscriber in ctool(portal_type = 'ENLSubscriber',
                                path='/'.join(self.context.getPhysicalPath()),
                                sort_on='email'):
            obj = subscriber.getObject()
            csvWriter.writerow([
                obj.salutation.encode("utf-8"),
                obj.fullname.encode("utf-8"),
                obj.email,
                obj.organization.encode("utf-8")])
        file.close()
        data = open(filename, "r").read()

        # Create response
        response = context.REQUEST.response
        response.addHeader('Content-Disposition', "attachment; filename=easynewsletter-subscribers.csv")
        response.addHeader('Content-Type', 'text/csv')
        response.addHeader('Content-Length', "%d" % len(data))
        response.addHeader('Pragma', "no-cache")
        response.addHeader('Cache-Control', "must-revalidate, post-check=0, pre-check=0, public")
        response.addHeader('Expires', "0")

        # Return CSV data
        return data
