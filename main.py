import webapp2
import jinja2
import os


from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api.images import get_serving_url
from google.appengine.datastore.datastore_query import Cursor


template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)

LIST_TAGS = ["All"]
LIST_TAG_UPDATED = False
MAX_IMAGE_GALLERY = 6


class Art(ndb.Model):
    title = ndb.StringProperty()
    image_key = ndb.BlobKeyProperty()
    image_url = ndb.StringProperty()
    tags = ndb.StringProperty(repeated=True)

    def _pre_put_hook(self):
        global LIST_TAGS
        for tag in self.tags:
            if tag not in LIST_TAGS:
                LIST_TAGS.append(tag)


def update_list_tags():
    global LIST_TAG_UPDATED
    global LIST_TAGS
    if not LIST_TAG_UPDATED:
        all_arts = Art.query()
        for art in all_arts.fetch(6):
            for tag in art.tags:
                if tag not in LIST_TAGS:
                    LIST_TAGS.append(tag)
        LIST_TAG_UPDATED = True


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def get_user(self):
        user = users.get_current_user()
        if user:
            self.response.headers['Content-Type'] = 'text/html'
            self.response.write('<!doctype html> <html> <p> Hello, ' + user.nickname() + "!You can <a href=\""
                                 + "/logout" +
                                 "\">sign out</a>.</p> </html>")
        else:
            self.response.write("<!doctype html> <html> <p> Hello,  you aren't log in yet !You can <a href=\""
                                 + users.create_login_url(self.request.uri) +
                                 "\">sign in</a>.</p> </html>")


class HomePage(Handler):
    def render_main(self, image_name="", image_url=""):
        self.render("home.html", image_name=image_name, image_url=image_url)

    def get(self):
        all_arts = Art.query().fetch(1)
        image_name = all_arts[0].title
        image_url = all_arts[0].image_url
        self.render_main(image_name, image_url)


class UploadFormHandler(Handler):
    def render_main(self, upload_url=""):
        self.render("upload_form.html", upload_url=upload_url)

    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        self.render_main(upload_url)


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        new_art = Art()
        new_art.title = self.request.get('image_name')
        # Get image data
        upload = self.get_uploads()[0]
        new_art.image_key = upload.key()
        new_art.image_url = get_serving_url(new_art.image_key)
        new_art.tags = self.request.get('image_tags').split()
        new_art.put()
        self.redirect('/private/upload_form')


class ViewArtHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, photo_key):
        if not blobstore.get(photo_key):
            self.error(404)
        else:
            self.send_blob(photo_key)


def query_list_image(cursor, select_tag):
    curs = Cursor(urlsafe=cursor)
    if select_tag == "All" or select_tag == "":
        all_arts, next_curs, more = Art.query().fetch_page(MAX_IMAGE_GALLERY, start_cursor=curs)
    else:
        all_arts, next_curs, more = Art.query(Art.tags == select_tag).fetch_page(MAX_IMAGE_GALLERY, start_cursor=curs)
    list_image = []
    for art in all_arts:
        list_image.append([art.image_url, art.key.urlsafe(), art.tags])
    if more and next_curs:
        return list_image, more, next_curs.urlsafe()
    else:
        return list_image, False, ""


class GalleryHandler(Handler):
    def render_main(self, list_image="", more=False, next_cursor="", tag=""):
        self.render("gallery.html", list_image=list_image, more=more, next_cursor=next_cursor, private="", list_tags=LIST_TAGS, select_tag=tag)

    def get(self):
        update_list_tags()
        cursor = self.request.get('cursor')
        select_tag = self.request.get('select_tag')
        list_image, more, next_cursor = query_list_image(cursor, select_tag)
        self.render_main(list_image, more, next_cursor, select_tag)


class ViewImageHandler(Handler):
    def render_main(self, image="", image_name="", key_urlsafe=""):
        self.render("view_image.html", image_url=image, image_name=image_name, key_urlsafe=key_urlsafe)

    def get(self, url_key):
        art_key = ndb.Key(urlsafe=url_key)
        art = art_key.get()
        image = art.image_url
        image_name = art.title
        key_urlsafe = art.key.urlsafe()
        self.render_main(image, image_name, key_urlsafe)


class PrivateGalleryHandler(Handler):
    def render_main(self, list_image="", more=False, next_cursor="", tag=""):
        self.render("gallery.html", list_image=list_image, more=more, next_cursor=next_cursor, private="/private", list_tags=LIST_TAGS, select_tag=tag)

    def get(self):
        update_list_tags()
        cursor = self.request.get('cursor')
        select_tag = self.request.get('select_tag')
        list_image, more, next_cursor = query_list_image(cursor, select_tag)
        self.render_main(list_image, more, next_cursor, select_tag)


class ModifyFormHandler(Handler):
    def render_main(self, url_key=""):
        art_key = ndb.Key(urlsafe=url_key)
        art = art_key.get()
        self.render("modify_form.html", art_title=art.title, art_tags=art.tags, art_image=art.image_url, art_key=url_key)

    def get(self, url_key):
        self.render_main(url_key)


class ModifyHandler(Handler):
    def post(self, url_key):
        art_key = ndb.Key(urlsafe=url_key)
        art = art_key.get()
        art.title = self.request.get('image_name')
        art.tags = self.request.get('image_tags').split()
        art.put()
        self.redirect('/private/modify_form/' + url_key)


class ContactHandler(Handler):
    def render_main(self):
        self.render("contact.html")

    def get(self):
        self.render_main()


class QuestionHandler(Handler):
    def render_main(self):
        self.render("question.html")

    def get(self):
        self.render_main()


class DonHandler(Handler):
    def render_main(self):
        self.render("don.html")

    def get(self):
        self.render_main()


class ExempleHandler(Handler):
    def render_main(self):
        self.render("exemple.html")

    def get(self):
        self.render_main()


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/view_art/([^/]+)?', ViewArtHandler),
    ('/view_image/([^/]+)?', ViewImageHandler),
    ('/gallery', GalleryHandler),
    ('/contact', ContactHandler),
    ('/questions', QuestionHandler),
    ('/don', DonHandler),
    ('/exemple', ExempleHandler),
    ('/private/gallery', PrivateGalleryHandler),
    ('/private/modify_form/([^/]+)?', ModifyFormHandler),
    ('/private/modify/([^/]+)?', ModifyHandler),
    ('/private/upload_form', UploadFormHandler),
    ('/upload', UploadHandler),
], debug=True)
