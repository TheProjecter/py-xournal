import sys, os
import urllib
import poppler
import cairo
import gzip
import xml.dom.minidom

class XournalDocument:
	def __init__(self):
		self.pages = []
		self.version = '0.4.5'
		self.width = 612.0
		self.height = 792.0
		self.title = 'Xournal document - see http://math.mit.edu/~auroux/software/xournal/'
		self.background_filename = ''

	def add_page(self):
		new_page = Page()
		self.pages.append(new_page)
		return new_page

	def get_page(self, num):
		if num >= len(self.pages):
			return self.add_page()
		else:
			return self.pages[num]

	def load_file(self, filename):
		filename = os.path.abspath(filename)

		try:
			with gzip.open(filename, 'rb') as f:
				xojdata = f.read()
		except IOError:
			with open(filename, 'rb') as f:
				xojdata = f.read()

		self.load_string(xojdata)

	def load_string(self, xojdata):
		dom = xml.dom.minidom.parseString(xojdata)
		#print dom.toxml()

		self.load_dom(dom)

	def load_dom(self,dom):
		# <xournal version="0.4.5">
		xournal = dom.getElementsByTagName('xournal')[0]
		self.version = xournal.getAttribute('version')
		self.title = getText(dom.getElementsByTagName('title')[0].childNodes)

		for page_dom in xournal.getElementsByTagName("page"):
			page = self.add_page()
			page.load_dom(page_dom)

			if self.width == 0.0 or self.height == 0.0:
				self.width = page.width
				self.height = page.height

			if page.background_type != 'solid':
				if self.background_filename != '' and page.background_filename == '':
					page.background_filename = self.background_filename
				elif self.background_filename == '' and page.background_filename != '':
					self.background_filename = page.background_filename

	def render_cairo(self, ctx):
		for page in self.pages:
			page.render_cairo(ctx)

	def render_xoj(self):
		xoj_output = []
		xoj_output.append('<?xml version="1.0" standalone="no"?>' + "\n")
		xoj_output.append('<xournal version="' + self.version + '">' + "\n")
		xoj_output.append('<title>' + self.title + '</title>' + "\n")

		for page in self.pages:
			xoj_output.append(page.render_xoj())

		xoj_output.append('</xournal>' + "\n")
		return ''.join(xoj_output)

class Page:
	def __init__(self):
		self.layers = []
		self.width = 0.0
		self.height = 0.0

		self.background_type = ''
		self.background_domain = ''
		self.background_filename = ''
		self.background_pageno = 0
		self.background_color = 'white'
		self.background_style = 'plain'
		self.background_domain = 'absolute'

	def add_layer(self):
		new_layer = Layer()
		self.layers.append(new_layer)
		return new_layer

	def get_layer(self, num):
		if num >= len(self.layers):
			self.add_layer()
			return self.layers[len(self.layers) - 1]
		else:
			return self.layers[num]

	def load_dom(self, dom):
		#<page width="612.00" height="792.00">
		self.width = float(dom.getAttribute('width'))
		self.height = float(dom.getAttribute('height'))

		bg_dom = dom.getElementsByTagName("background")[0]

		self.background_type = bg_dom.getAttribute('type')

		if self.background_type == 'solid': # place holders for now
			#<background type="solid" color="white" style="lined" />
			self.background_color = bg_dom.getAttribute('color')
			self.background_style = bg_dom.getAttribute('style')
		elif self.background_type == 'pdf':
			#<background type="pdf" domain="absolute" filename="/home/gs/pyxournal/COMLEX-workshop1.pdf" pageno="1" />
			#<background type="pdf" pageno="2" />
			self.background_domain = bg_dom.getAttribute('domain')
			background_filename = bg_dom.getAttribute('filename')
			self.background_pageno = int(bg_dom.getAttribute('pageno'))

			if background_filename != '':
				self.background_filename = os.path.abspath(background_filename)

		for layer_dom in dom.getElementsByTagName("layer"):
			layer = self.add_layer()
			layer.load_dom(layer_dom)

	def render_cairo(self, ctx):
		if self.background_type == 'pdf' and self.background_filename != '':
			pdf_filename = os.path.abspath(self.background_filename)
			pdf_uri = 'file://%s' % urllib.pathname2url(pdf_filename)
			pdfdoc = poppler.document_new_from_file(pdf_uri, password=None)

			pdf_page = pdfdoc.get_page(self.background_pageno - 1)
			pdf_page.render_for_printing(ctx)

		for layer in self.layers:
			layer.render_cairo(ctx)

		ctx.show_page()

	def render_xoj(self):
		#<page width="612.00" height="792.00">

		#<background type="solid" color="white" style="lined" />
		#<background type="pdf" domain="absolute" filename="/home/gs/pyxournal/COMLEX-workshop1.pdf" pageno="1" />
		#<background type="pdf" pageno="2" />

		xoj_output = []
		xoj_output.append('<page width="' + str(self.width) + '" height="' + str(self.height) + '">' + "\n")

		if self.background_type == 'pdf':
			if self.background_pageno > 1:
				xoj_output.append('<background type="' + self.background_type + '" pageno="' + str(self.background_pageno) + '" />' + "\n")
			else:
				xoj_output.append('<background type="' + self.background_type + '" domain="' + self.background_domain + '" filename="' + self.background_filename + '" pageno="' + str(self.background_pageno) + '" />' + "\n")
		elif self.background_type == 'solid':
			xoj_output.append('<background type="' + self.background_type + '" color="' + self.background_color + '" style="' + self.background_style + '" />' + "\n")

		if self.layers != []:
			for layer in self.layers:
				xoj_output.append(layer.render_xoj())
		else:
			xoj_output.append('<layer></layer>' + "\n")

		xoj_output.append('</page>' + "\n")
		return ''.join(xoj_output)

class Layer:
	def __init__(self):
		self.items = []

	def add_stroke(self):
		new_stroke = Stroke()
		self.items.append(new_stroke)
		return new_stroke

	def add_text(self):
		new_text = Text()
		self.items.append(new_text)
		return new_text

	def load_dom(self, dom):
		for item_dom in dom.getElementsByTagName("*"):
			if item_dom.tagName == 'stroke':
				new_stroke = self.add_stroke()
				new_stroke.load_dom(item_dom)
			elif item_dom.tagName == 'text':
				new_text = self.add_text()
				new_text.load_dom(item_dom)

	def render_cairo(self, ctx):
		for item in self.items:
			item.render_cairo(ctx)

	def render_xoj(self):
		xoj_output = []
		xoj_output.append('<layer>' + "\n")

		for item in self.items:
			xoj_output.append(item.render_xoj())

		xoj_output.append('</layer>' + "\n")
		return ''.join(xoj_output)


class Item:
	def __init__(self):
		self.red = 0
		self.green = 0
		self.blue = 0
		self.alpha = 0
		self.hexcolor = '#000000ff'

	def string_to_color(self, color_string):
		if color_string[0] == '#':
			red = int('0x' + color_string[1] + color_string[2], 0)
			green = int('0x' + color_string[3] + color_string[4], 0)
			blue = int('0x' + color_string[5] + color_string[6], 0)
			alpha = int('0x' + color_string[7] + color_string[8], 0)
		elif color_string == 'black':
			return self.string_to_color('#000000ff')
		elif color_string == 'blue':
			return self.string_to_color('#0000ffff')
		elif color_string == 'red':
			return self.string_to_color('#ff0000ff')
		elif color_string == 'green':
			return self.string_to_color('#008000ff')
		elif color_string == 'gray':
			return self.string_to_color('#808080ff')
		elif color_string == 'lightblue':
			return self.string_to_color('#add8e6ff')
		elif color_string == 'lightgreen':
			return self.string_to_color('#90ee90ff')
		elif color_string == 'magenta':
			return self.string_to_color('#8b008bff')
		elif color_string == 'orange':
			return self.string_to_color('#ffa500ff')
		elif color_string == 'yellow':
			return self.string_to_color('#ffff00ff')
		elif color_string == 'white':
			return self.string_to_color('#ffffffff')

		return red, green, blue, alpha

class Stroke (Item):
	def __init__(self):
		self.points = []
		self.tool = 'pen'

		Item.__init__(self)

	def load_dom(self, dom):
		#<stroke tool="pen" color="#002a40ff" width="0.85">
		#<stroke tool="highlighter" color="yellow" width="8.50">
		self.tool = dom.getAttribute('tool')

		self.red, self.green, self.blue, self.alpha = self.string_to_color(dom.getAttribute('color'))

		if self.tool == 'highlighter' and self.alpha > 200:
			self.alpha = int(.4 * self.alpha)

		self.hexcolor = "#" + hex(self.red)[2:].rjust(2,'0') + hex(self.green)[2:].rjust(2,'0') + hex(self.blue)[2:].rjust(2,'0') + hex(self.alpha)[2:].rjust(2,'0')

		width_list = dom.getAttribute('width').split()
		point_list = getText(dom.childNodes).split()

		while width_list != [] and point_list != []:
			tmp_w = float(width_list.pop(0))
			tmp_x = float(point_list.pop(0))
			tmp_y = float(point_list.pop(0))
			self.points.append((tmp_x, tmp_y, tmp_w))

		while point_list != []:
			# tmp_w set from previous point
			tmp_x = float(point_list.pop(0))
			tmp_y = float(point_list.pop(0))
			self.points.append((tmp_x, tmp_y, tmp_w))

	def render_cairo(self, ctx):
		old_operator = ctx.get_operator()

		if self.tool == 'highlighter':
			ctx.set_operator(cairo.OPERATOR_SATURATE)

		ctx.set_source_rgba(self.red/255.0, self.green/255.0, self.blue/255.0, self.alpha/255.0)

		ctx.stroke()
		x, y, width = self.points[len(self.points) - 1]
		ctx.set_line_width(width)
		ctx.move_to(x, y)

		for x, y, width in reversed(self.points):
			if ctx.get_line_width() != width:
				ctx.line_to(x, y)
				ctx.stroke()
				ctx.move_to(x, y)
				ctx.set_line_width(width)
			else:
				ctx.line_to(x, y)

		ctx.stroke()

		ctx.set_operator(old_operator)

	def render_xoj(self):
		#<stroke tool="pen" color="#002a40ff" width="0.85">
		#<stroke tool="highlighter" color="yellow" width="8.50">
		xoj_output = []

		widths = []
		points = []
		for x, y, width in self.points:
			widths.append(str(width))
			points.append(str(x))
			points.append(str(y))

		xoj_output.append('<stroke tool="' + self.tool + '" color = "' + self.hexcolor + '" width="' + ' '.join(widths) + '">')
		xoj_output.append(' '.join(points))
		xoj_output.append('</stroke>' + "\n")

		return ''.join(xoj_output)

class Text (Item):
	def __init__(self):
		self.font = ''
		self.size = 0
		self.x = 0.0
		self.y = 0.0
		self.text = ''

		Item.__init__(self)

	def load_dom(self, dom):
		#<text font="Sans" size="12.00" x="55.50" y="105.00" color="#002a40ff">
		self.font = dom.getAttribute('font')
		self.size = float(dom.getAttribute('size'))
		self.x = float(dom.getAttribute('x'))
		self.y = float(dom.getAttribute('y'))

		self.red, self.green, self.blue, self.alpha = self.string_to_color(dom.getAttribute('color'))
		self.hexcolor = "#" + hex(self.red)[2:].rjust(2,'0') + hex(self.green)[2:].rjust(2,'0') + hex(self.blue)[2:].rjust(2,'0') + hex(self.alpha)[2:].rjust(2,'0')

		self.text = getText(dom.childNodes)

	def render_cairo(self, ctx):
		#<text font="Sans" size="12.00" x="55.50" y="105.00" color="#002a40ff">
		ctx.select_font_face(self.font)
		ctx.set_font_size(self.size)
		ctx.set_source_rgba(self.red/255.0, self.green/255.0, self.blue/255.0, self.alpha/255.0)

		text_y = self.y

		for text in self.text.split("\n"):
			text_y += self.size
			ctx.move_to(self.x, text_y)
			ctx.show_text(text)

	def render_xoj(self):
		#<text font="Sans" size="12.00" x="55.50" y="105.00" color="#002a40ff">
		xoj_output = []

		xoj_output.append('<text font="' + self.font + '" size = "' + self.size + '" x="' + self.x + '" y="' + self.y + '" color="' + self.hexcolor + '">')
		xoj_output.append(self.text)
		xoj_output.append('</text>' + "\n")

		return ''.join(xoj_output)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def getText(nodelist):
	rc = []
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc.append(node.data)
	return ''.join(rc)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == "__main__":
	if len(sys.argv) != 2:
		 print("Usage: %s <filename>")
		 sys.exit()

	input_filename = sys.argv[1]
	output_filename = os.path.splitext(os.path.basename(sys.argv[1]))[0] + '-%.3d.pdf'

	xojdoc = XournalDocument()
	xojdoc.load_file(input_filename)

	fo = open(output_filename % 0, 'wb')

	surface = cairo.PDFSurface (fo, xojdoc.width, xojdoc.height)

	ctx = cairo.Context(surface)
	ctx.set_line_join(cairo.LINE_JOIN_ROUND)
	ctx.set_line_cap(cairo.LINE_CAP_ROUND)

	#ctx.translate(50.0, 50.0)

	xojdoc.render_cairo(ctx);

	surface.finish()
