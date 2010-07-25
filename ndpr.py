#!/usr/bin/env python

import sys, os, re
from BeautifulSoup import BeautifulSoup
import urllib2
import subprocess, tempfile, shutil
from optparse import OptionParser
import logging

class LatexFailedError(Exception):
    pass

class LRBParser:
    format = { "title":"LRB" }

    def extract(self,txt):
        s = BeautifulSoup(txt)
        for x in s.findAll(style="display:none"):
            x.extract()

        i=s.find('div',"article-body indent")
        t=s.find('title')
        i=("<html>" + str(t) + "<body>" + str(i) + "</body></html>")
        return str(i)

class NDPRParser:
    format = { "title":"NDPR" }

    def extract(self,txt):
        txt = re.sub("</?o:p>","",txt)
        txt = re.sub("&(?!\w*;)","&amp;",txt)

        soup = BeautifulSoup(txt)
        soup = soup.find('div',id="review")
        for tag in soup.findAll("a"):
            tag.replaceWith(tag.renderContents())

        return str(soup)

def runLatex(html):
    tmpdir = tempfile.mkdtemp(prefix="offprint")
    try:
        i = tmpdir + "/i.html"
        o = tmpdir + "/o.tex"
        p = tmpdir + "/o.pdf"
        l = tmpdir + "/o.log"
        template = os.path.dirname(__file__) + "/latex.template"

        f = open(i, "wb")
        f.write(html)
        f.close()

        subprocess.check_call(["pandoc", "-f", "html", "-st", "latex", "--xetex",
            "--template=" + template, "-o", o, i])
        code = subprocess.call(["xelatex", "-interaction=batchmode", "-output-directory", tmpdir, o])

        if code != 0:
            print("Warning: latex returned error code %s" % code)
            logging.warning(open(l,"r").read())

        if not os.path.exists(p):
            raise LatexFailedError("No PDF generated.")

        pdf = open(p, "rb").read()
        if len(pdf) < 1000:
            raise LatexFailedError("Invalid PDF")
    finally:
        shutil.rmtree(tmpdir)
    
    return pdf

def convert(url):
    logging.debug("Retrieving url '%s'" % url)
    html = urllib2.urlopen(url).read()
    logging.debug("Parsing")
    typeparser = NDPRParser()
    html = typeparser.extract(html)
    logging.debug("Running latex")
    pdf = runLatex(html)
    logging.debug("Done.")
    return pdf

def main():
    parser = OptionParser("usage: %prog [options] URL/file out.pdf")

    parser.add_option("-n","--ndpr",action="store_const",dest="type",const="ndpr",
        help="Notre Dame Philosophical Review")
    parser.add_option("-l","--lrb",action="store_const",dest="type",const="lrb",
        help="London Review of Books")
    parser.add_option("-x","--extract",action="store_true",dest="extract",
        help="Extract only (don't generate pdf)")
    parser.set_defaults(type="ndpr")

    (options,args) = parser.parse_args()
    if len(args) < 1:
        parser.error("incorrect number of arguments")

    a = args[0]
    try:
        of = args[1]
    except IndexError:
        if options.extract:
            print("You need to specify an output file name.")
            sys.exit(1)

        if a.lower().startswith("http://"):
            of = "out.pdf"
        else:
            root = os.path.splitext(os.path.basename(a))[0]
            of = root + ".pdf"

    if options.type == "lrb":
        typeparser = LRBParser()
    else:
        typeparser = NDPRParser()

    if a.lower().startswith("http://"):
        print("Fetching URL: " + a)
        f = urllib2.urlopen(a).read()
    else:
        f = open(a).read()

    print("Read %d bytes." % len(f))

    # extract information
    s=typeparser.extract(f)

    if options.extract:
        print("Writing %s..." % of)
        f = open(of,"w")
        f.write(s)
        f.close()
    else:
        try:
            pdf = runLatex(s)
        except LatexFailedError:
            print("Error: Latex command failed to generate PDF file.")
            sys.exit(1)

        print("Writing %s..." % of)
        f=open(of,"w")
        f.write(pdf)
        f.close()

if __name__ == "__main__":
    main()
