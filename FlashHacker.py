import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'FlowGrapher'))
os.environ['PATH'] = os.path.join(os.path.dirname(os.path.realpath(__file__)),r'Bin\GraphViz') + \
					';' + \
					os.path.join(os.path.dirname(os.path.realpath(__file__)),'FlowGrapher') + \
					';' + \
					os.environ['PATH']
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtSql import *
import os
import subprocess
import shutil

from FlashManipulation import *
from Graphs import *

class CodeEdit(QTextEdit):
	def __init__(self,parent=None):
		super(CodeEdit,self).__init__(parent)

	def showDisasms(self,blocks,labels):
		disasm_text=''
		block_ids=blocks.keys()
		block_ids.sort()
		for block_id in block_ids:
			if labels.has_key(block_id):
				disasm_text+='%s:\n'% labels[block_id]

			for [op,operand] in blocks[block_id]:
				disasm_text+='\t%s' % (op)
				if operand:
					disasm_text+='\t%s' % operand
				disasm_text+='\n'
			disasm_text+='\n'
				
		self.setText(disasm_text)

class InstrumentOptionDialog(QDialog):
	def __init__(self,parent=None,asasm=None):
		super(InstrumentOptionDialog,self).__init__(parent)
		self.setWindowTitle("Instrument Option")

		self.method_cb=QCheckBox('Methods',self)
		self.bb_cb=QCheckBox('Basic Blocks',self)
		self.api_cb=QCheckBox('APIs',self)

		self.apiTreeView=QTreeView()
		[local_names,api_names,multi_names,multi_namels]=asasm.GetNames()
		self.apiTreeModel=TreeModel(("Name",),checkable=True)
		self.apiTreeModel.showAPIs(api_names,multi_namels,show_call_op=True,single_column=True,show_caller=True)
		self.apiTreeView.setModel(self.apiTreeModel)
		#self.apiTreeView.expandAll()			

		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)

		main_layout=QGridLayout()
		main_layout.addWidget(self.method_cb,0,0)
		main_layout.addWidget(self.bb_cb,1,0)
		main_layout.addWidget(self.api_cb,2,0)
		main_layout.addWidget(self.apiTreeView,3,0)
		main_layout.addWidget(buttonBox,4,0)

		self.setLayout(main_layout)
		self.resize(950,500)

	def keyPressEvent(self,e):
		key=e.key()

		if key in [Qt.Key_Return, Qt.Key_Enter]:
			return
		else:
			super(InstrumentOptionDialog,self).keyPressEvent(e)

	def GetCheckState(self):
		checked={'Method':False,'BasicBlock':False,'API':False}
		if self.method_cb.isChecked():
			checked['Method']=True
		if self.bb_cb.isChecked():
			checked['BasicBlock']=True
		if self.api_cb.isChecked():
			checked['API']=True

		return checked

	def GetCheckedItemData(self):
		return self.apiTreeModel.GetCheckedItemData()

class ConfigurationDialog(QDialog):
	def __init__(self,parent=None,rabcdasm='',log_level=0):
		super(ConfigurationDialog,self).__init__(parent)
		self.setWindowTitle("Configuration")
		self.setWindowIcon(QIcon('DarunGrim.png'))

		rabcdasm_button=QPushButton('RABCDAsm Path:',self)
		rabcdasm_button.clicked.connect(self.getRABCDasmPath)
		self.rabcdasm_line=QLineEdit("")
		self.rabcdasm_line.setAlignment(Qt.AlignLeft)
		self.rabcdasm_line.setMinimumWidth(250)
		self.rabcdasm_line.setText(rabcdasm)

		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)

		main_layout=QGridLayout()
		main_layout.addWidget(rabcdasm_button,0,0)
		main_layout.addWidget(self.rabcdasm_line,0,1)

		main_layout.addWidget(buttonBox,6,1)

		self.setLayout(main_layout)

	def keyPressEvent(self,e):
		key=e.key()

		if key in [Qt.Key_Return, Qt.Key_Enter]:
			return
		else:
			super(ConfigurationDialog,self).keyPressEvent(e)

	def getRABCDasmPath(self):
		if dir_name := QFileDialog.getExistingDirectory(self, 'FileStore Dir'):
			self.rabcdasm_line.setText(dir_name)

class TreeItem(object):
	def __init__(self,data,parent=None,assoc_data=None,checked=Qt.Unchecked):
		self.parentItem=parent
		self.checked=checked
		self.itemData=data
		self.assocData=assoc_data
		self.childItems=[]

	def appendChild(self,item):
		self.childItems.append(item)

	def child(self,row):
		return self.childItems[row]

	def childCount(self):
		return len(self.childItems)

	def children(self):
		return self.childItems

	def columnCount(self):
		return len(self.itemData)

	def setAssocData(self,data):
		self.assocData=data

	def getAssocData(self):
		return self.assocData

	def setChecked(self,checked):
		self.checked=checked

	def getChecked(self):
		return self.checked

	def data(self,column):
		try:
			return self.itemData[column]
		except:
			import traceback
			traceback.print_exc()

	def parent(self):
		return self.parentItem

	def row(self):
		return self.parentItem.childItems.index(self) if self.parentItem else 0

class TreeModel(QAbstractItemModel):
	def __init__(self,root_item,parent=None,checkable=False):
		super(TreeModel, self).__init__(parent)
		self.Checkable=checkable
		self.DirItems={}
		self.rootItem=TreeItem(root_item)
		self.setupModelData()

	def addDir(self,dir):
		dir_item=TreeItem((os.path.basename(dir),))
		self.rootItem.appendChild(dir_item)
		self.DirItems[dir]=dir_item

		asasm=ASASM()
		for relative_file in asasm.EnumDir(dir):
			item=TreeItem((relative_file,),dir_item)
			dir_item.appendChild(item)

	def showClasses(self,assemblies):
		for root_dir in assemblies.keys():
			class_names=assemblies[root_dir].keys()
			class_names.sort()

			for class_name in class_names:
				dir_item=TreeItem((class_name,))
				self.rootItem.appendChild(dir_item)

				[parsed_lines,methods]=assemblies[root_dir][class_name]
				for [refid,[blocks,maps,labels,parents,body_parameters]] in methods.items():
					item=TreeItem((refid,),dir_item,(root_dir, class_name, refid))
					dir_item.appendChild(item)

	def showAPIs(self,api_names,multi_namels,show_call_op=False,single_column=False,show_caller=True):
		api_names_list=api_names.keys()
		api_names_list.sort()
		for api_name in api_names_list:
			first_entry=True
			for [op,root_dir,class_name,refid,block_id,block_line_no] in api_names[api_name]:
				if show_call_op and not op.startswith('call'):
					continue

				if first_entry:
					item_data=[api_name,]
					if not single_column:
						item_data.append("API")
					dir_item=TreeItem(item_data)

					self.rootItem.appendChild(dir_item)
					first_entry=False

				if show_caller:
					item_data=[refid,]
					if not single_column:
						item_data.append(op)				
					item=TreeItem(item_data,dir_item,(op,root_dir,class_name,refid,block_id,block_line_no),checked=Qt.Checked)
					dir_item.appendChild(item)

		for multi_namel in multi_namels.keys():
			added_root=False
			for [op,root_dir,class_name,refid,block_id,block_line_no] in multi_namels[multi_namel]:
				if op.startswith('call'):
					if not added_root:
						item_data=[multi_namel,]
						if not single_column:
							item_data.append("Dynamic")

						dir_item=TreeItem(item_data)
						self.rootItem.appendChild(dir_item)
						added_root=True

					if show_caller:
						item_data=[refid,]
						if not single_column:
							item_data.append(op)

						item=TreeItem(item_data,dir_item,(op,root_dir,class_name,refid,block_id,block_line_no),checked=Qt.Checked)
						dir_item.appendChild(item)

	def GetCheckedItemData(self):
		data=[]
		for l1_item in self.rootItem.children():
			if l1_item.getChecked()==Qt.Checked:
				data.extend(
					l2_item.getAssocData()
					for l2_item in l1_item.children()
					if l2_item.getChecked() == Qt.Checked
				)
		return data

	DebugShowTrace=0
	def showTrace(self,repeat_info_list):
		last_call_stack=[]
		node_map={}

		color=None
		for repeat_info in repeat_info_list:
			if self.DebugShowTrace>0:
				print 'New Repeat Info:'

			index=0
			for call_stack in repeat_info['callstack']:
				if self.DebugShowTrace>0:
					for call_stack_line in call_stack:
						print '\t',call_stack_line

				new_node_map={}
				last_root_item=self.rootItem
				for i in range(0,len(call_stack),1):
					if self.DebugShowTrace>0:
						print '\tAdding:',call_stack[i], '\tKey:',call_stack[0:i+1]

					node_key=str(call_stack[0:i+1])

					if node_map.has_key(node_key):
						last_root_item=node_map[node_key]
					else:
						if index==0 and i==len(call_stack)-1:
							repeated_str=str(repeat_info['repeated'])
							#start of new section
							if repeat_info['repeated']==1:
								color=QColor(Qt.white)
							else:
								if color==QColor(Qt.yellow) or color==QColor(Qt.white):
									color=QColor(Qt.green)
								else:
									color=QColor(Qt.yellow)
						else:
							repeated_str=''

						new_item=TreeItem((call_stack[i],repeated_str),last_root_item,assoc_data=color)

						node_map[node_key]=new_item
						last_root_item.appendChild(new_item)
						last_root_item=new_item

					new_node_map[node_key]=last_root_item

				node_map=new_node_map

				j=0
				while j<min(len(call_stack),len(last_call_stack)):
					if call_stack[j]!=last_call_stack[j]:
						break
					j+=1
				if self.DebugShowTrace>0:
					print '\tCommon stack list:',j,call_stack[0:j]
					print ''

				last_call_stack=call_stack

				index+=1

			if self.DebugShowTrace>0:						
				print '\t',repeat_info['repeated']
				print ''

	def setupModelData(self):
		pass

	def setData(self,index,value,role):
		if role==Qt.CheckStateRole and index.column()==0:
			item=index.internalPointer()

			if value==0:
				item.setChecked(Qt.Unchecked)
			else:
				item.setChecked(Qt.Checked)
			self.dataChanged.emit(index, index)

		return True

	def columnCount(self,parent):
		if parent.isValid():
			return parent.internalPointer().columnCount()
		else:
			return self.rootItem.columnCount()

	def getAssocData(self,index):
		if not index.isValid():
			return None

		item=index.internalPointer()
		return item.getAssocData()

	def data(self,index,role):
		if not index.isValid():
			return None

		if role==Qt.BackgroundRole:
			item=index.internalPointer()
			return item.getAssocData()
		elif role==Qt.CheckStateRole and self.Checkable:
			if index.column()==0:
				item=index.internalPointer()
				checked=item.getChecked()

				return Qt.Checked if checked==Qt.Checked else Qt.Unchecked
		elif role==Qt.DisplayRole:
			item=index.internalPointer()
			return item.data(index.column())

		return None

	def headerData(self,section,orientation,role):
		if orientation==Qt.Horizontal and role==Qt.DisplayRole:
			return self.rootItem.data(section)

		return None

	def index(self,row,column,parent):
		if not self.hasIndex(row,column,parent):
			return QModelIndex()

		parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
		if childItem := parentItem.child(row):
			return self.createIndex(row,column,childItem)
		else:
			return QModelIndex()

	def parent(self,index):
		if not index.isValid():
			return QModelIndex()

		childItem=index.internalPointer()
		parentItem=childItem.parent()

		if parentItem is None:
			return QModelIndex()
		else:
			return (
				QModelIndex()
				if parentItem == self.rootItem
				else self.createIndex(parentItem.row(), 0, parentItem)
			)

	def rowCount(self,parent):
		if parent.column()>0:
			return 0

		parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
		return parentItem.childCount()

	def flags(self,index):
		if not index.isValid():
			return Qt.NoItemFlags

		ret=Qt.ItemIsEnabled|Qt.ItemIsSelectable
		if index.column()==0:
			ret|=Qt.ItemIsUserCheckable

		return ret

class MainWindow(QMainWindow):
	UseDock=False
	ShowBBMatchTableView=False

	def __init__(self):
		super(MainWindow,self).__init__()
		self.setWindowTitle("Flash Hacker")
		self.readSettings()

		self.asasm=ASASM()

		self.treeModel=None
		self.SWFFilename=''
		self.SWFOutFilename=''

		vertical_splitter=QSplitter()
		vertical_splitter.setOrientation(Qt.Vertical)
		# Left Tab
		horizontal_splitter=QSplitter()

		self.leftTabWidget=QTabWidget()

		self.classTreeView=QTreeView()
		self.leftTabWidget.addTab(self.classTreeView,"Classes")

		self.apiTreeView=QTreeView()
		self.leftTabWidget.addTab(self.apiTreeView,"API")

		self.traceTreeView=QTreeView()
		self.leftTabWidget.addTab(self.traceTreeView,"Trace")

		horizontal_splitter.addWidget(self.leftTabWidget)

		# Right Tab
		self.rightTabWidget=QTabWidget()
		self.rightTabWidget.connect(self.rightTabWidget,SIGNAL("currentChanged(int)"), self.rightTabWidgetIndexChanged)

		self.graph=MyGraphicsView()
		self.graph.setRenderHints(QPainter.Antialiasing)

		self.codeEdit=CodeEdit()
		self.rightTabWidget.addTab(self.codeEdit,"Code")
		self.rightTabWidget.addTab(self.graph,"Graph")

		horizontal_splitter.addWidget(self.rightTabWidget)
		horizontal_splitter.setStretchFactor(0,0)
		horizontal_splitter.setStretchFactor(1,1)

		vertical_splitter.addWidget(horizontal_splitter)
		self.logWidget=QTextEdit()
		vertical_splitter.addWidget(self.logWidget)
		vertical_splitter.setStretchFactor(0,1)
		vertical_splitter.setStretchFactor(1,0)
		
		main_widget=QWidget()
		vlayout=QVBoxLayout()
		vlayout.addWidget(vertical_splitter)
		main_widget.setLayout(vlayout)
		self.setCentralWidget(main_widget)
		
		self.createMenus()

		self.restoreUI()
		self.show()

	DebugFileOperation=0
	def open(self):
		if filename := QFileDialog.getOpenFileName(
			self, "Open SWF", "", "SWF Files (*.swf)|All Files (*.*)"
		)[0]:
			self.openSWF(filename)

	def reload(self):
		self.openSWF(self.SWFFilename,reload=True)

	def logCallback(self,message):
		self.logWidget.append(message)
		
	def openSWF(self,filename,reload=True):
		self.SWFFilename=filename
		self.leftTabWidget.setCurrentIndex(0)
		swf_file=SWFFile(self.RABCDAsmPath,self.logCallback)
		self.showDir(swf_file.ExtractSWF(filename))

	def saveAs(self):
		self.SWFOutFilename=''
		self.save()

	def save(self):
		if self.DebugFileOperation>0:	
			print 'self.SWFFilename:',self.SWFFilename

		if self.SWFFilename:
			if not self.SWFOutFilename:
				target_root_dir=os.path.dirname(self.SWFFilename)
				self.SWFOutFilename=QFileDialog.getSaveFileName(self,'Save File',target_root_dir,'SWF (*.swf *.*)')[0]
		
			swf_file=SWFFile(self.RABCDAsmPath,self.logCallback)
			swf_file.PackSWF(self.SWFFilename,self.SWFOutFilename)

	def openDirectory(self):
		dialog=QFileDialog()
		dialog.setFileMode(QFileDialog.Directory)
		dialog.setOption(QFileDialog.ShowDirsOnly)
		if directory := dialog.getExistingDirectory(
			self, "Choose Directory", os.getcwd()
		):
			self.showDir([directory])

	def performInstrument(self):
		#Show dialog
		dialog=InstrumentOptionDialog(asasm=self.asasm)
		if dialog.exec_():
			checked=dialog.GetCheckState()

			if checked['API'] or checked['BasicBlock'] or checked['Method']:
				target_root_dir=os.path.dirname(self.SWFFilename)

				instrumented=False

				if checked['API']:
					checked_items=dialog.GetCheckedItemData()
					locator={}
					for [op,root_dir,class_name,refid,block_id,block_line_no] in checked_items:
						if not locator.has_key(refid):
							locator[refid]={}

						if not locator[refid].has_key(block_id):
							locator[refid][block_id]={}

						if not locator[refid][block_id].has_key(block_line_no):
							locator[refid][block_id][block_line_no]=True

					self.asasm.Instrument(operations=[["AddAPITrace",{'Locator':locator}]])
					instrumented=True

				if checked['BasicBlock']:
					self.asasm.Instrument(operations=[["AddBasicBlockTrace",'']])
					instrumented=True

				elif checked['Method']:
					self.asasm.Instrument(operations=[["AddMethodTrace",'']])
					instrumented=True

				if instrumented:
					self.asasm.Instrument(operations=[["Include",["../Util-0/Util.script.asasm"]]])
					self.asasm.Save(target_root_dir=target_root_dir)
					self.saveAs()

	def loadLogTrace(self):
		self.leftTabWidget.setCurrentIndex(2)
		if filename := QFileDialog.getOpenFileName(
			self, "Open Log file", "", "Log Files (*.txt)|All Files (*.*)"
		)[0]:
			repeat_info_list=self.asasm.LoadLogFile(filename)

			[local_names,api_names,multi_names,multi_namels]=self.asasm.GetNames()
			self.traceTreeModel=TreeModel(("Stack","Count"))
			self.traceTreeModel.showTrace(repeat_info_list)
			self.traceTreeView.setModel(self.traceTreeModel)
			#self.traceTreeView.connect(self.traceTreeView.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.apiTreeSelected)
			self.traceTreeView.expandAll()
			self.traceTreeView.setColumnWidth(0,300)
			self.traceTreeView.setColumnWidth(1,10)

	def createMenus(self):
		self.fileMenu=self.menuBar().addMenu("&File")
		self.openAct=QAction("&Open SWF file...",
									self,
									triggered=self.open)
		self.fileMenu.addAction(self.openAct)

		self.reloadAct=QAction("&Reload...",
									self,
									triggered=self.reload)
		self.fileMenu.addAction(self.reloadAct)

		self.openDirAct=QAction("&Open directory...",
									self,
									shortcut=QKeySequence.Open,
									statusTip="Open an existing folder", 
									triggered=self.openDirectory)
		self.fileMenu.addAction(self.openDirAct)
		self.instrumentMenu=self.menuBar().addMenu("&Instrument")

		self.performInstrumentAct=QAction("&Perform Instrument...",
									self,
									triggered=self.performInstrument)
		self.instrumentMenu.addAction(self.performInstrumentAct)

		self.traceMenu=self.menuBar().addMenu("&Trace")

		self.addLoadLogAct=QAction("&Load log file...",
									self,
									triggered=self.loadLogTrace)
		self.traceMenu.addAction(self.addLoadLogAct)

	def showDir(self,dirs):
		self.Assemblies=self.asasm.RetrieveAssemblies(dirs)

		self.treeModel=TreeModel(("Name",))
		self.treeModel.showClasses(self.Assemblies)
		self.classTreeView.setModel(self.treeModel)
		self.classTreeView.connect(self.classTreeView.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.classTreeSelected)
		self.classTreeView.expandAll()

		[local_names,api_names,multi_names,multi_namels]=self.asasm.GetNames()
		self.apiTreeModel=TreeModel(("Name",""))
		self.apiTreeModel.showAPIs(api_names,multi_namels,True)
		self.apiTreeView.setModel(self.apiTreeModel)
		self.apiTreeView.connect(self.apiTreeView.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.apiTreeSelected)
		self.apiTreeView.expandAll()

	def ShowCode(self,tab_index):
		if not self.treeModel:
			return

		item_data=self.treeModel.getAssocData(self.currentClassTreeIndex)
		if item_data!=None:
			(root_dir,class_name,refid)=item_data
			[parsed_lines,methods]=self.Assemblies[root_dir][class_name]
			(blocks,maps,labels,parents,body_parameters)=methods[refid]

			if tab_index==0:
				self.codeEdit.showDisasms(blocks,labels)

			elif tab_index==1:
				show_graph=True
				if len(blocks)>200:
					msgBox=QMessageBox()
					msgBox.setText("Too many nodes")
					msgBox.setInformativeText("The graph is too big, do you want to display?")
					msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
					msgBox.setDefaultButton(QMessageBox.No)
					ret = msgBox.exec_()

					show_graph = ret == QMessageBox.Yes
				if show_graph:
					[disasms,links,address2name]=self.asasm.ConvertMapsToPrintable(methods[refid])				
					self.graph.DrawFunctionGraph("Target", disasms, links, address2name=address2name)

	def classTreeSelected(self,newSelection,oldSelection):
		for index in newSelection.indexes():
			self.currentClassTreeIndex=index
			self.ShowCode(self.rightTabWidget.currentIndex())

	def rightTabWidgetIndexChanged(self,index):
		left_tab_index=self.leftTabWidget.currentIndex()
		if left_tab_index==0:
			self.ShowCode(index)
		elif left_tab_index==1:
			self.showCodeForApiTree(index)

	def showCodeForApiTree(self,tab_index):
		if not self.treeModel:
			return

		item_data=self.treeModel.getAssocData(self.currentAPITreeIndex)
		if item_data!=None:
			(op,root_dir,class_name,refid,block_id,block_line_no)=item_data
					
			[parsed_lines,methods]=self.Assemblies[root_dir][class_name]
			(blocks,maps,labels,parents,body_parameters)=methods[refid]

			if tab_index==0:
				self.codeEdit.showDisasms(blocks,labels)

			elif tab_index==1:
				[parsed_lines,methods]=self.Assemblies[root_dir][class_name]
				[disasms,links,address2name]=self.asasm.ConvertMapsToPrintable(methods[refid])
				self.graph.DrawFunctionGraph("Target", disasms, links, address2name=address2name)
				self.graph.HilightAddress(block_id)

	def apiTreeSelected(self, newSelection, oldSelection):
		for index in newSelection.indexes():
			self.currentAPITreeIndex=index
			self.showCodeForApiTree(self.rightTabWidget.currentIndex())

	def showConfiguration(self):
		dialog=ConfigurationDialog(rabcdasm=self.RABCDAsmPath)
		if dialog.exec_():
			self.RABCDAsmPath=dialog.rabcdasm_line.text()
			return True
		return False

	def readSettings(self):
		settings=QSettings("DarunGrim LLC", "FlashHacker")

		default_rabcdasm_path=os.path.join(os.path.dirname(os.path.realpath(__file__)),r'Bin\RABCDasm')
		self.RABCDAsmPath=default_rabcdasm_path
		if settings.contains("General/RABCDAsmPath") and settings.value("General/RABCDAsmPath"):
			self.RABCDAsmPath=settings.value("General/RABCDAsmPath")
			rabcdasm=os.path.join(self.RABCDAsmPath,"rabcdasm.exe")
			if not os.path.isfile(rabcdasm):
				self.RABCDAsmPath=default_rabcdasm_path

				rabcdasm=os.path.join(self.RABCDAsmPath,"rabcdasm.exe")
				if not os.path.isfile(rabcdasm):
					self.showConfiguration()

		self.FirstConfigured=False
		if settings.contains("General/FirstConfigured"):
			self.FirstConfigured=True

		elif self.showConfiguration():
			self.FirstConfigured=True
		self.ShowGraphs=True
		if settings.contains("General/ShowGraphs"):
			self.ShowGraphs = settings.value("General/ShowGraphs") == 'true'
							
	def saveSettings(self):
		settings = QSettings("DarunGrim LLC", "FlashHacker")
		settings.setValue("General/ShowGraphs", self.ShowGraphs)
		settings.setValue("General/RABCDAsmPath", self.RABCDAsmPath)

		if self.FirstConfigured==True:
			settings.setValue("General/FirstConfigured", self.FirstConfigured)

	def closeEvent(self, event):
		self.saveSettings()
		self.saveUI()
		QMainWindow.closeEvent(self, event)

	def changeEvent(self,event):
		if event.type()==QEvent.WindowStateChange:
			if (self.windowState()&Qt.WindowMinimized)==0 and \
				 (self.windowState()&Qt.WindowMaximized)==0 and \
				 (self.windowState()&Qt.WindowFullScreen)==0 and \
				 (self.windowState()&Qt.WindowActive)==0:
					pass

	def resizeEvent(self,event):
		if not self.isMaximized():
			self.NonMaxGeometry=self.saveGeometry()

	def restoreUI(self):
		settings=QSettings("DarunGrim LLC", "FlashHacker")
		
		if settings.contains("geometry/non_max"):
			self.NonMaxGeometry=settings.value("geometry/non_max")
			self.restoreGeometry(self.NonMaxGeometry)
		else:
			self.resize(800,600)
			self.NonMaxGeometry=self.saveGeometry()
		
		if settings.contains("isMaximized"):
			if settings.value("isMaximized")=="true":
				self.setWindowState(self.windowState()|Qt.WindowMaximized)
		self.restoreState(settings.value("windowState"))

	def saveUI(self):
		settings=QSettings("DarunGrim LLC", "FlashHacker")
		if self.NonMaxGeometry!=None:
			settings.setValue("geometry/non_max", self.NonMaxGeometry)
		settings.setValue("isMaximized", self.isMaximized())
		settings.setValue("windowState", self.saveState())

if __name__=='__main__':
	import sys
	import time

	app=QApplication(sys.argv)
	#pixmap=QPixmap('DarunGrimSplash.png')
	#splash=QSplashScreen(pixmap)
	#splash.show()
	app.processEvents()
	window=MainWindow()

	if len(sys.argv)>1:
		for filename in sys.argv[1:]:
			if os.path.isfile(filename):
				window.openSWF(filename)
			else:
				window.showDir(filename)

	window.show()
	#splash.finish(window)
	sys.exit(app.exec_())
