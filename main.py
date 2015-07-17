import webapp2
import jinja2
import os


from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api.images import get_serving_url

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


class Art(ndb.Model):
    title = ndb.StringProperty()
    image_key = ndb.BlobKeyProperty()
    image_url = ndb.StringProperty()
    tags = ndb.StringProperty(repeated=True)


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
    def render_main(self, image=""):
        self.render("home.html", image=image)

    def get(self):
        all_arts = Art.query()
        for art in all_arts:
            image = art.image_url
            break
        self.render_main(image)


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
        #self.redirect('/view_art/%s' % upload.key())
        self.redirect('/upload_form')


class ViewArtHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, photo_key):
        if not blobstore.get(photo_key):
            self.error(404)
        else:
            self.send_blob(photo_key)


class GalleryHandler(Handler):
    def render_main(self, list_image=""):
        self.render("gallery.html", list_image=list_image)

    def get(self):
        all_arts = Art.query()
        list_image = []
        count = 0
        max_image = 10
        for art in all_arts:
            list_image.append([art.image_url, art.key.urlsafe()])
            count += 1
            if count == max_image:
                break
        self.render_main(list_image)


class ViewImageHandler(Handler):
    def render_main(self, image=""):
        self.render("view_image.html", image=image)

    def get(self, url_key):
        art_key = ndb.Key(urlsafe=url_key)
        art = art_key.get()
        image = art.image_url
        self.render_main(image)


class PrivateGalleryHandler(Handler):
    def render_main(self, list_image=""):
        self.render("private_gallery.html", list_image=list_image)

    def get(self):
        all_arts = Art.query()
        list_image = []
        count = 0
        max_image = 10
        for art in all_arts:
            list_image.append([art.image_url, art.key.urlsafe(), art.tags])
            count += 1
            if count == max_image:
                break
        self.render_main(list_image)


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


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/upload_form', UploadFormHandler),
    ('/upload', UploadHandler),
    ('/view_art/([^/]+)?', ViewArtHandler),
    ('/view_image/([^/]+)?', ViewImageHandler),
    ('/gallery', GalleryHandler),
    ('/private/gallery', PrivateGalleryHandler),
    ('/private/modify_form/([^/]+)?', ModifyFormHandler),
    ('/private/modify/([^/]+)?', ModifyHandler)
], debug=True)
