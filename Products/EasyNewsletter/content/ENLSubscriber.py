from AccessControl import ClassSecurityInfo
from Products.Archetypes import atapi
from zope.interface import implements
from Products.CMFCore.utils import getToolByName

from Products.EasyNewsletter import config
from Products.EasyNewsletter.interfaces import IENLSubscriber
from Products.EasyNewsletter import EasyNewsletterMessageFactory as _
from Products.validation.interfaces import ivalidator
from Products.validation import validation


class NoDuplicateValidator(object):
    __implements__ = (ivalidator, )

    name = 'noDuplicateContent'
    title = 'Prevent duplicated content'
    description = 'Prevent duplicated content'

    def __call__(self, value=None, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance is not None:
            folder = instance.aq_parent
            identifier = getToolByName(instance, 'plone_utils').normalizeString(value).lower()
            if folder._getOb(identifier, instance) != instance:
                return _(u"Duplicate registration.")
        return 1

validation.register(NoDuplicateValidator())


schema = atapi.BaseSchema + atapi.Schema((

    atapi.StringField('title',
        required = False,
        widget = atapi.StringWidget(
            visible = {'edit': 'invisible', 'view': 'invisible'},
            label = _(u'EasyNewsletter_label_title', default=u'Title'),
            description = _(u'EasyNewsletter_help_title', default=u''),
            i18n_domain = 'EasyNewsletter',
        ),
    ),

     atapi.StringField('salutation',
        required = False,
        vocabulary = config.SALUTATION,
        widget = atapi.SelectionWidget(
            label = _(u'EasyNewsletter_label_salutation',
                default='Salutation'),
            description = _('EasyNewsletter_help_salutation', default=u''),
            i18n_domain = 'EasyNewsletter',
            format = 'select',
        ),
    ),

    atapi.StringField('fullname',
        required = False,
        widget = atapi.StringWidget(
            label = _(u'EasyNewsletter_label_fullname', default=u'Full Name'),
            description = _('EasyNewsletter_help_fullname', default=u''),
            i18n_domain = 'EasyNewsletter',
        ),
    ),

    atapi.StringField('organization',
        required = False,
        widget = atapi.StringWidget(
            label = _(u'EasyNewsletter_label_organization',
                default=u'Company/Organization'),
            description = _('EasyNewsletter_help_organization',
                default=u''),
            i18n_domain = 'EasyNewsletter',
        ),
    ),

    atapi.StringField('email',
        required = True,
        validators = ('isEmail', 'noDuplicateContent'),
        widget = atapi.StringWidget(
            label = _(u'EasyNewsletter_label_email',
                default=u'Emaileuuuh'),
            description = _(u'EasyNewsletter_help_email',
                default=u''),
            i18n_domain = 'EasyNewsletter',
        ),
    ),

), )


class ENLSubscriber(atapi.BaseContent):
    """An newsletter subscriber.
    """
    implements(IENLSubscriber)
    security = ClassSecurityInfo()
    schema = schema
    _at_rename_after_creation = True

    def generateNewId(self):
        return getToolByName(self, 'plone_utils').normalizeString(self.email).lower()

    def setEmail(self, value):
        """
        """
        self.email = value
        self.title = value

        # reindex to set title for catalog
        self.reindexObject()

    def Title(self):
        """Overwritten accessor for Title
        """
        title_str = self.getEmail()
        if self.getFullname():
            title_str += ' - ' + self.getFullname()
        return title_str


atapi.registerType(ENLSubscriber, config.PROJECTNAME)
