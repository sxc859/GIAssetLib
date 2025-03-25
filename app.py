import os
import sys
import math
import json
import HoyoDL
import tempfile
import requests
import subprocess
from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from indexHelper import IndexHelper

class ExtractThread(QThread):
	progress = pyqtSignal(list)
	finished = pyqtSignal(dict)

	def __init__(self, data):
		super().__init__()
		self.data = data

	def run(self):
		path = lambda *args: os.path.join(*args)
		cwd = os.getcwd()

		# STEP 1 - Download the blk
		self.data["progressLabel"].setText("Downloading...")
		downloadDir = self.data["downloadDir"].name
		downloaded = 0

		for index, dl in enumerate(self.data["dls"]):
			filePath = os.path.join(downloadDir, os.path.basename(dl.url))
			os.makedirs(downloadDir, exist_ok=True)

			with open(filePath, "wb") as file:

				for data in dl.iter_content(1024):
					file.write(data)
					downloaded += len(data)

					self.progress.emit([downloaded, self.data["totalSize"], True])

		# STEP 2 - Extract the assets
		self.data["progressLabel"].setText("Extracting...")

		# command
		assets = self.data["assets"]
		pos = 0

		for asset in assets:
			args = [
				path(cwd, "studio", "AssetStudio.CLI.exe"),
				path(downloadDir, f'{asset["source"]["block"]}.blk'),
				self.data["outputFolder"],
				"--game",
				"GI",
				"--types",
				asset["type"],
				"--names",
				asset["name"],
				"--containers",
				asset["container"],
				"--group_assets",
				"None"
			]

			subprocess.call(args, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
			pos += 1
			self.progress.emit([pos, len(assets), False])

		# Done
		self.data["progressLabel"].setText("Idle")

		self.finished.emit({
			"downloadDir": self.data["downloadDir"],
			"outputFolder": self.data["outputFolder"]
		})

class Popup(QDialog):
	def __init__(self, parent=None, text=""):
		super().__init__(parent)
		self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
		self.setModal(True)
		self.setStyleSheet("QDialog { border: 2px solid black; }")

		layout = QVBoxLayout(self)
		label = QLabel(text)
		label.setStyleSheet("font-size: 24px; font-weight: bold;")
		layout.addWidget(label)

class GIAssetLib(QMainWindow):
	def __init__(self):
		super(GIAssetLib, self).__init__()
		uic.loadUi("gui.ui", self)

		self.hoyoClient = HoyoDL()
		self.hoyoClient.setGame("hk4e")

		with open("config.json", "r") as f:
			self.config = json.loads(f.read())
			f.close()

		self.setWindowTitle(f'GIAssetLib | v{self.config["version"]}')
		self.setupUi()

	def setupUi(self):
		self.selectFolder = lambda: QFileDialog.getExistingDirectory(self, "Select Folder")
		self.selectFile = lambda: QFileDialog.getOpenFileName(self, "Select File", "", "Index Files (*.index)")[0]

		self.loadIndexBtn.clicked.connect(self.loadIndexFile)
		self.searchBtn.clicked.connect(self.updateSearch)
		self.extractBtn.clicked.connect(self.extractItems)

		self.fullTable = True
		self.updateAssetTable({})

	###

	def loadIndexFile(self):
		file = self.selectFile()
		if file != "":
			self.updateAssetTable({})
			failed = False
			popup = Popup(self, "Parsing the index file...")
			popup.show()
			QApplication.processEvents()
			try:
				indexData = IndexHelper(file)
			except:
				failed = True
			popup.close()

			if failed:
				QMessageBox.warning(None, "Warning", "Invalid index file !", QMessageBox.Ok)
				self.updateLoadedStatus(False)
			else:
				self.updateLoadedStatus(True)
				self.indexData = indexData
				self.hoyoClient.setVersion(self.indexData.version)
				self.infosLabel.setText(f"Loaded v{self.indexData.version} | {len(self.indexData.assets)} assets")
				self.updateAssetTable(self.indexData.assets)

	def updateLoadedStatus(self, status):
		self.nameLineEdit.setEnabled(status)
		self.typeLineEdit.setEnabled(status)
		self.searchBtn.setEnabled(status)
		self.extractBtn.setEnabled(status)
		self.assetsList.setEnabled(status)

	def updateAllStatus(self, status):
		self.updateLoadedStatus(status)
		self.loadIndexBtn.setEnabled(status)

	def updateAssetTable(self, data):
		popup = Popup(self, "Refreshing list...")
		popup.show()
		QApplication.processEvents()

		self.assetsList.horizontalHeader().setStretchLastSection(True)
		self.assetsList.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.assetsList.setRowCount(len(data))
		self.assetsList.setColumnCount(2)
		self.assetsList.setHorizontalHeaderLabels(["Name", "Type"])

		for row, (key, value) in enumerate(data.items()):
			self.assetsList.setItem(row, 0, QTableWidgetItem(str(key)))
			self.assetsList.setItem(row, 1, QTableWidgetItem(str(value["type"])))

		self.assetsList.resizeColumnsToContents()
		self.assetsList.clearSelection()
		popup.close()

	def updateSearch(self):
		nameSearch = self.nameLineEdit.text()
		typeSearch = self.typeLineEdit.text()

		if nameSearch == "" and typeSearch == "":
			if not self.fullTable:
				self.updateAssetTable(self.indexData.assets)
			self.fullTable = True
			return

		filtered = {k: v for k, v in self.indexData.assets.items() if nameSearch.lower() in k.lower() and typeSearch.lower() in v.get("type", "").lower()}
		self.fullTable = False
		self.updateAssetTable(filtered)

	def convertSize(self, size, precision = 2):
		isize = int(size)

		if isize < 1024:
			return f"{isize} B"
		elif isize / 1024 < 1024:
			return f"{round(isize / 1024, precision)} KB"
		elif isize / 1048576 < 1024:
			return f"{round(isize / 1048576, precision)} MB"
		elif isize / 1073741824 < 1024:
			return f"{round(isize / 1073741824, precision)} GB"
		else:
			return f"{round(isize / 1099511627776, precision)} TB"

	def extractItems(self):
		selectedItems = self.assetsList.selectedItems()

		if len(selectedItems) == 0:
			QMessageBox.information(None, "Information", "No assets selected !", QMessageBox.Ok)
			return

		selectedTexts = [item.text() for item in selectedItems if item.column() == 0]
		selectedAssets = []
		for e in selectedTexts:
			asset = self.indexData.assets[e]
			asset["name"] = e
			selectedAssets.append(asset)

		# get all required blk to download
		blocks = list(set([e["source"]["block"] for e in selectedAssets]))
		size = 0
		folders = {}
		for block in blocks:
			infos = self.indexData.getBlockInfos(block)
			size += infos["size"]
			folders[block] = infos["folder"]

		userConfirm = QMessageBox.question(None, "Confirmation", f"The tool will need to download {self.convertSize(size)} of data to extract the selected assets, continue ?", QMessageBox.Yes | QMessageBox.No)

		# if user agrees, let's go :D
		if userConfirm == QMessageBox.Yes:
			dls = [self.hoyoClient.downloadBlock(f"{folders[e]}/{e}") for e in blocks]
			downloadDir = tempfile.TemporaryDirectory()

			outputFolder = self.selectFolder()

			if outputFolder == "":
				QMessageBox.warning(None, "Aborted !", "User aborted the operation", QMessageBox.Ok)
				return

			workerData = {
				"dls": dls,
				"downloadDir": downloadDir,
				"totalSize": size,
				"outputFolder": outputFolder,
				"progressLabel": self.progressLabel,
				"assets": selectedAssets
			}

			self.updateAllStatus(False)

			self.backgroundThread = QThread()
			self.backgroundWorker = ExtractThread(workerData)
			self.backgroundWorker.moveToThread(self.backgroundThread)
			self.backgroundThread.started.connect(self.backgroundWorker.run)
			self.backgroundWorker.finished.connect(self.handleFinished)
			self.backgroundWorker.finished.connect(self.backgroundThread.quit)
			self.backgroundWorker.finished.connect(self.backgroundWorker.deleteLater)
			self.backgroundThread.finished.connect(self.backgroundThread.deleteLater)

			self.backgroundWorker.progress.connect(self.progressBarSlot)
			self.backgroundThread.start()

	@pyqtSlot(list)
	def progressBarSlot(self, progress):
		percentage = (progress[0] / progress[1]) * 100
		self.progressBar.setValue(math.ceil(percentage))

		_format = f"{percentage:.2f}%"
		if progress[2]:
			_format = f"{percentage:.2f}% - {self.convertSize(progress[0])} / {self.convertSize(progress[1])}"
		
		self.progressBar.setFormat(_format)

	@pyqtSlot(dict)
	def handleFinished(self, data):
		data["downloadDir"].cleanup()
		self.updateAllStatus(True)
		os.startfile(data["outputFolder"])

if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = GIAssetLib()
	window.show()
	sys.exit(app.exec_())