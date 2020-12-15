"""
Small application for uploading files to a server.

Inspired by: http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
"""

import logging
import os
import time
import urllib
from pathlib import Path

from flask import (Blueprint, Markup, current_app, flash, redirect, render_template, request, send_from_directory,
                   url_for, session)
from werkzeug.utils import secure_filename

general = Blueprint("general", __name__)
log = logging.getLogger("validatems" + __name__)


@general.route("/hello")
def hello_world():
    """Render index.html and write message 'Hello!'."""
    log.debug("Hello!")
    flash("Hello!", category="success")
    return render_template("index.html")


@general.route("/", methods=["GET", "POST"])
def upload_file():
    """Render index.html and define upload routines."""
    if request.method == "POST":
        session.clear()
        try:
            # URL upload
            if "url" in request.form:
                # User did not specify any URL
                if not request.form["url"]:
                    flash("No URL supplied!", category="warning")
                    log.warning("No URL input!")
                    return redirect(request.url)

                else:
                    upload_url = request.form["url"]
                    try:
                        contenttype = get_content_type(upload_url)
                    except Exception as e:
                        log.exception("Unexpected error with URL: %s Error was: %s" % (upload_url, e))
                        flash("Something went wrong. Are you sure your URL is valid?", category="error")
                        return redirect(request.url)

                    # Wrong content type
                    if not content_is_xml(contenttype):
                        flash("This URL does not seem to contain XML!", category="error")
                        log.warning("Invalid content type in: %s" % (upload_url))
                        return redirect(request.url)

                    filename = create_filename(url=upload_url)
                    log.debug("Upload %s from URL: %s" % (filename, upload_url))
                    save_as = Path.joinpath(Path(current_app.instance_path), filename)
                    urllib.request.urlretrieve(upload_url, save_as)
                    validate_meta_share(save_as)

            # Local file upload
            else:
                upload_file = request.files["file"]

                # User did not select a file
                if not upload_file:
                    flash("No file selected!", category="warning")
                    log.warning("No file selected!")
                    return redirect(request.url)
                else:
                    filename = create_filename(secure_filename(upload_file.filename))
                    # File looks good, upload!
                    if file_valid(filename):
                        log.debug("Uploading file: %s" % filename)
                        save_as = Path.joinpath(Path(current_app.instance_path), filename)
                        upload_file.save(save_as)
                        validate_meta_share(save_as)

        # Unexpected error
        except Exception as e:
            log.exception("Unexpected error: %s" % e)
            flash("Something went wrong :(", category="error")
            return redirect(request.url)

    return render_template("index.html")


def validate_meta_share(fileobj):
    """Validate uploaded XML against META-SHARE xsd schema."""
    from lxml import etree

    xmlschema_doc = etree.parse("validatems/static/META-SHARE-Resource.xsd")
    xmlschema = etree.XMLSchema(xmlschema_doc)

    xml_doc = etree.parse(str(fileobj))
    try:
        xmlschema.assertValid(xml_doc)
        flash(Markup("File '%s' validated!" % fileobj.name), category="success")
    except Exception as e:
        errormsg = str(e).replace("{http://www.ilsp.gr/META-XMLSchema}", "")
        log.error("Validation error for: '%s':<br>%s" % (fileobj.name, errormsg))
        flash(Markup("Validation error for: '%s':<br>%s" % (fileobj.name, errormsg)), category="error")


def file_valid(filename):
    """Check if a file is valid for upload, print error messages otherwise."""
    # Invalid file extension
    if not ("." in filename and filename.rsplit(".", 1)[1].lower() == "xml"):
        log.error("Invalid file extension for file: %s" % filename)
        flash("%s: invalid file extension! Only XML is allowed." % filename, category="error")
        return False
    return True


def get_content_type(url):
    """Get the content type from a URL."""
    # Add headers to pretend to be a browser, some pages block crawling
    hdr = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
           "Accept-Encoding": "none",
           "Accept-Language": "en-US,en;q=0.8",
           "Connection": "keep-alive"}
    req = HeadRequest(url, headers=hdr)
    log.debug("Request: %s" % req)
    response = urllib.request.urlopen(req)
    log.debug("Response: %s" % response)
    maintype = response.headers["Content-Type"].split(";")[0].lower()
    log.debug("Maintype: %s" % maintype)
    return maintype


class HeadRequest(urllib.request.Request):
    def get_method(self):
        return "HEAD"


def content_is_xml(maintype):
    """Check if HTML content type is an image."""
    return maintype in ("text/xml", "application/xml")


def create_filename(in_filename=None, url=None):
    """Create filename from current date and time."""
    extension = ".xml"
    if url:
        in_filename = url.split("/")[-1]
    if not in_filename:
        in_filename = time.strftime("%Y-%m-%d_%H%M%S") + extension
    # Filename exists, add int
    filename = in_filename
    n = 0
    while filename in os.listdir(current_app.instance_path):
        n += 1
        filename = in_filename.rsplit(".", 1)[0] + str(n) + extension
    return filename
