import sys
import pprint

from PySide.QtGui import *
from PySide.QtCore import *
import FlowGrapher

TYPE_DI_RECTS=0
TYPE_DI_DRAW=1
TYPE_DI_GRAPH=2

TYPE_DI_COLOR=3
TYPE_DI_FILLCOLOR=4
TYPE_DI_BGCOLOR=5
TYPE_DI_FONTCOLOR=6

class GraphScene(QGraphicsScene):
	Debug=0
	def __init__(self,parent=None):
		QGraphicsScene.__init__(self,parent)
		self.setBackgroundBrush(Qt.white)
		self.BlockRects={}
		self.SelectedAddress=None
		self.GraphRect=[0,0,0,0]

	def InvertedQPointF(self,x,y):
		return QPointF(x,self.GraphRect[3]-y)

	def Draw(self,flow_grapher):
		self.clear()
		self.setSceneRect(-180,-90,360,180)
		flow_grapher.GenerateDrawingInfo()
		len=flow_grapher.GetDrawingInfoLength()

		pen_color=''
		font_size=''
		font_name=''

		self.BlockRects={}
		self.SelectedAddress=None
		self.GraphRect=[0,0,0,0]

		for i in range(0,len,1):
			di=flow_grapher.GetDrawingInfoMember(i)

			if di.type==TYPE_DI_GRAPH:
				self.GraphRect=[di.GetPoint(0).x, di.GetPoint(0).y,di.GetPoint(1).x, di.GetPoint(1).y]
				self.setSceneRect(QRectF(di.GetPoint(0).x, di.GetPoint(0).y,di.GetPoint(1).x, di.GetPoint(1).y))

			if di.type==TYPE_DI_COLOR:
				pen_color=di.text

			if di.type==TYPE_DI_FILLCOLOR:
				fill_color=di.text

			if di.type==TYPE_DI_BGCOLOR:
				bg_color=di.text

			if di.type==TYPE_DI_FONTCOLOR:
				font_color=di.text

			if di.type==TYPE_DI_RECTS:
					polygon=QPolygonF()
					for j in range(0, di.count,1):
						polygon.append(self.InvertedQPointF(di.GetPoint(j).x, di.GetPoint(j).y))

					pen=QPen(QColor(pen_color))
					brush=QBrush(QColor(bg_color))
					#self.addPolygon(polygon, pen, brush)

			if di.type==TYPE_DI_DRAW:
				type_ch=chr(di.subtype)
				if type_ch=='L':
					start_x=di.GetPoint(0).x
					start_y=di.GetPoint(0).y

					end_x=di.GetPoint(1).x
					end_y=di.GetPoint(1).y

					if self.Debug>0:
						print 'Line %d,%d - %d,%d' % (di.GetPoint(0).x, di.GetPoint(0).y, di.GetPoint(1).x, di.GetPoint(1).y)
					
					line=QGraphicsLineItem(QLineF(self.InvertedQPointF(start_x,start_y),self.InvertedQPointF(end_x,end_y)))
					line.setPen(QPen(Qt.black))
					self.addItem(line)

				elif type_ch=='P' or type_ch=='p':
					polygon=QPolygonF()
					for j in range(0, di.count,1):
						x=di.GetPoint(j).x
						y=di.GetPoint(j).y

						if di.count==4:
							if not self.BlockRects.has_key(di.address):
								self.BlockRects[di.address]=[0xffffffff,0xffffffff,0,0]

							if self.BlockRects[di.address][0]>x:
								self.BlockRects[di.address][0]=x

							if self.BlockRects[di.address][1]>y:
								self.BlockRects[di.address][1]=y

							if self.BlockRects[di.address][2]<x:
								self.BlockRects[di.address][2]=x

							if self.BlockRects[di.address][3]<y:
								self.BlockRects[di.address][3]=y

						polygon.append(self.InvertedQPointF(x,y))

					pen=None
					brush=None
					if pen_color:
						pen=QPen(self.GetColor(pen_color))

					if type_ch=='P' and fill_color!='':
						if self.Debug>0:
							print type_ch, fill_color
						brush=QBrush(self.GetColor(fill_color))

					self.addPolygon(polygon, pen, brush)

				elif type_ch=='B' or type_ch=='b':
					if self.Debug>0:
						print 'Bezier:'
						for j in range(0, di.count,1):
							print '\t%d,%d' % (di.GetPoint(j).x, di.GetPoint(j).y)

					for i in range(0,di.count-1,3):
						path=QPainterPath(self.InvertedQPointF(di.GetPoint(i).x, di.GetPoint(i).y))
					
						path.cubicTo(
										self.InvertedQPointF(di.GetPoint(i+1).x, di.GetPoint(i+1).y),
										self.InvertedQPointF(di.GetPoint(i+2).x, di.GetPoint(i+2).y),
										self.InvertedQPointF(di.GetPoint(i+3).x, di.GetPoint(i+3).y)
									)
						self.addPath(path);

				elif type_ch=='F':
					font_size=di.size
					font_name=di.text

				elif type_ch=='c':
					pen_color=di.text

				elif type_ch=='C':
					fill_color=di.text

				elif type_ch=='T':
					if self.Debug>0:
						print "%s %s %s %s" % (di.text, font_name, font_size, pen_color)

					text_item=QGraphicsTextItem()

					if pen_color:
						text_item.setDefaultTextColor(self.GetColor(pen_color))

					font=QFont(font_name)
					font.setPixelSize(font_size)
					text_item.setFont(font)
					text_item.setPlainText(di.text)
					w=text_item.boundingRect().width()
					#text_item.setPos(di.GetPoint(0).x-w/2, (self.GraphRect[3] - di.GetPoint(0).y) - font_size - 3 )
					text_item.setPos(di.GetPoint(0).x-10, (self.GraphRect[3] - di.GetPoint(0).y) - font_size - 3 )
					self.addItem(text_item)

	def FindPolygon(self,address):
		return self.BlockRects[address] if self.BlockRects.has_key(address) else None

	def FindAddress(self,x,y):
		y=self.GraphRect[3]-y

		return next(
			(
				address
				for address, [
					start_x,
					start_y,
					end_x,
					end_y,
				] in self.BlockRects.items()
				if x > start_x and x < end_x and y > start_y and y < end_y
			),
			None,
		)

	def GetColor(self, color_str):
		if color_str:
			if color_str[0]=='#':
				color_name = color_str[:7]

				try:
					alpha=int(color_str[7:],16)
				except:
					pass
			else:
				color_name=color_str
				alpha=0xff

		color=QColor(color_name)
		color.setAlpha(alpha)
		return color

	def mousePressEvent(self,event):
		(x,y)=event.scenePos().x(), event.scenePos().y()
		self.SelectedAddress=self.FindAddress(x,y)

class MyGraphicsView(QGraphicsView):
	def __init__(self):
		self.scene=GraphScene()
		QGraphicsView.__init__(self,self.scene)
		self.SelectBlockCallback=None
		self.setStyleSheet("QGraphicsView { background-color: rgb(99.5%, 99.5%, 99.5%); }")
		self.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
		self.setDragMode(self.ScrollHandDrag)
		self.last_items=[]

	def wheelEvent(self,event):
		modifiers = QApplication.keyboardModifiers()
		if modifiers == Qt.ControlModifier:
			self.setTransformationAnchor(self.AnchorUnderMouse)

			scaleFactor=1.15

			if	event.delta()>0:
				self.scale(scaleFactor,scaleFactor)
			else:
				self.scale(1.0/scaleFactor, 1.0/scaleFactor)
		else:
			vsb=self.verticalScrollBar()
			dy=((-event.delta()/2)/15)* vsb.singleStep()
			vsb.setSliderPosition(vsb.sliderPosition()+dy)

	def clearLastItems(self):
		for item in self.last_items:
			try:
				self.scene.removeItem(item)
			except:
				pass
		self.last_items=[]

	def clear(self):
		self.clearLastItems()
		self.scene.clear()

	def SetDatabaseName(self,database_name):
		self.DatabaseName=database_name

	def DrawFunctionGraph(self,type,disasms,links,match_info=None,address2name=None):
		flow_grapher=FlowGrapher.FlowGrapher()

		for (address,[end_address,disasm]) in disasms.items():
			if (
				match_info != None
				and match_info.has_key(address)
				and match_info[address][1] != 100
			):
				flow_grapher.SetNodeShape("black", "yellow", "Verdana", "12")
			elif (
				match_info != None
				and match_info.has_key(address)
				and match_info[address][1] == 100
				or match_info is None
			):
				flow_grapher.SetNodeShape("black", "white", "Verdana", "12")
			else:
				flow_grapher.SetNodeShape("white", "red", "Verdana", "12")
			if address2name!=None and address2name.has_key(address):
				name=address2name[address] + "\\l"
			else:
				name="%.8X\\l" % address

			disasm = '\\l'.join(disasm.split('\n'))
			flow_grapher.AddNode(address, name, disasm)

		for (src,dsts) in links.items():
			for dst in dsts:
				flow_grapher.AddLink(src,dst)
		self.scene.Draw(flow_grapher)

	def DrawRect(self,start_x, start_y, end_x, end_y):
		polygon=QPolygonF()
		polygon.append(self.scene.InvertedQPointF(start_x,start_y))
		polygon.append(self.scene.InvertedQPointF(end_x,start_y))
		polygon.append(self.scene.InvertedQPointF(end_x,end_y))
		polygon.append(self.scene.InvertedQPointF(start_x,end_y))

		pen=QPen(self.scene.GetColor("green"))
		brush=QBrush(self.scene.GetColor("green"))
		self.last_items.append(self.scene.addPolygon(polygon, pen, brush))

	def HilightAddress(self,address,center=True):
		rect=self.scene.FindPolygon(address)
		if rect!=None:
			[start_x, start_y, end_x, end_y]=rect
			self.clearLastItems()

			self.DrawRect(start_x-5, start_y-5, start_x,end_y+5)
			self.DrawRect(end_x+5, start_y-5, end_x, end_y+5)

			self.DrawRect(start_x,start_y-5,end_x,start_y)
			self.DrawRect(start_x,end_y,end_x,end_y+5)

			if center:
				self.centerOn(self.scene.InvertedQPointF((start_x+end_x)/2,(start_y+end_y)/2))

	def SetSelectBlockCallback(self,callback):
		self.SelectBlockCallback=callback

	def mousePressEvent(self,event):
		QGraphicsView.mousePressEvent(self,event)
		if self.scene.SelectedAddress is not None and self.SelectBlockCallback is not None:
			self.HilightAddress(self.scene.SelectedAddress,False)
			self.SelectBlockCallback(self,self.scene.SelectedAddress)

	def SaveImg(self,filename):
		[start_x,start_y,end_x,end_y]=self.scene.GraphRect
		img=QImage(end_x,end_y,QImage.Format_ARGB32_Premultiplied)
		p=QPainter(img)
		self.scene.render(p)
		p.end()
		img.save(filename)

if __name__=='__main__':
	class MainWindow(QMainWindow):
		def __init__(self):
			QMainWindow.__init__(self)

			self.PatchedFunctionGraph=MyGraphicsView()
			self.PatchedFunctionGraph.setRenderHints(QPainter.Antialiasing)
			disasms={1:[2,"AAA"],2:[3,"BBB"]}
			links={1:[2]}
			address2name={1: "Address 1",2: "Address 2"}
			self.PatchedFunctionGraph.DrawFunctionGraph("Target", disasms, links, address2name=address2name)
			layout=QHBoxLayout()
			layout.addWidget(self.PatchedFunctionGraph)

			"""
			#scene=FunctionGraphScene()
			#self.scene=scene

			flow_grapher=FlowGrapher.FlowGrapher()
			flow_grapher.SetNodeShape("black", "white", "Verdana", "10")
			flow_grapher.AddNode(0, "Test 0", "Disasm lines")
			flow_grapher.AddNode(1, "Test 1", "Disasm lines")
			flow_grapher.AddNode(2, "Test 2", "Disasm lines")
			flow_grapher.AddNode(3, "Test 3", "Disasm lines")
			flow_grapher.AddLink(0,1)
			flow_grapher.AddLink(0,2)
			flow_grapher.AddLink(0,3)
			flow_grapher.AddLink(1,3)
			flow_grapher.AddLink(1,4)
			scene.Draw(flow_grapher)
			self.view=QGraphicsView(self.scene)
			self.view.setRenderHints(QPainter.Antialiasing)
			layout.addWidget(self.view)
			"""
			self.widget=QWidget()
			self.widget.setLayout(layout)

			self.setCentralWidget(self.widget)
			self.setWindowTitle("Graph")
			self.setWindowIcon(QIcon('DarunGrim.png'))

	app=QApplication(sys.argv)
	frame=MainWindow()
	frame.setGeometry(100,100,800,500)
	frame.show()
	sys.exit(app.exec_())

