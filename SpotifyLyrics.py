# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal, QThread, QRect
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLabel, QTextBrowser, QMenuBar, QMenu, \
    QStatusBar, QAction, QCheckBox
from bs4 import BeautifulSoup
from SwSpotify import spotify as sp
from time import sleep
import re
import requests
import webbrowser
import xml.etree.ElementTree as ET
import os

excluded_words = ['(feat', 'feat.', 'ft.', 'ft' 'remix', 'Remix', 'REMIX', '(with', 'with', 'prod.', '(prod.)']
token = 'xH2Z42wGA3vr1FAgsy7NuZ71hNdJco3XEFnQNrfwNK_Qq0WP8jvoqQbuvtuif265'

settings_path = './settings/settings.xml'

info_msg = 'Your lyrics will show up here!'
error_msg = 'Nothing is playing at the moment!'
got_error = False

searched_song_info = ""
curr_lyrics = info_msg

changed = False
last_song = ""
last_artist = ""

curr_song = ''
curr_artist = ''

auto_search = 'False'

try:
    tree = ET.parse(settings_path)
    root = tree.getroot()
    auto_search = root[0].text
except FileNotFoundError:
    os.mkdir('settings')
    f = open(settings_path, 'x')
    settings = ET.Element('settings')
    auto1 = ET.SubElement(settings, 'auto', attrib={'setting': 'auto_search'}).text = 'False'
    tree = ET.ElementTree(settings)
    tree.write(settings_path)
    auto_search = 'False'
except Exception as e:
    print(e)


class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setFixedSize(800, 685)
        self.setWindowTitle("Spotify Lyrics Finder")
        icon = QIcon("logo.ico")
        self.setWindowIcon(icon)

        self.CenterPanel = UiPanel(self)
        self.setCentralWidget(self.CenterPanel)

        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, 800, 21))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setTitle("File")
        self.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(self)
        self.statusbar.setSizeGripEnabled(False)
        self.setStatusBar(self.statusbar)
        self.actionClose = QAction(self)
        self.actionClose.setText("Close")
        self.actionClose.setShortcut("Ctrl+Q")
        self.actionProject = QAction(self)
        self.actionProject.setText("Copyright © White Aspect")
        self.menuFile.addAction(self.actionClose)
        self.menubar.addAction(self.menuFile.menuAction())

        self.actionClose.triggered.connect(close_app)
        self.actionProject.triggered.connect(project_website)


class UiPanel(QWidget):
    def __init__(self, parent):
        global last_song, last_artist

        QWidget.__init__(self)
        self.Parent = parent

        self.searchLyricsBtn = QPushButton("Search for lyrics!", self)
        self.searchLyricsBtn.setGeometry(QRect(510, 570, 280, 71))
        self.searchLyricsBtn.setEnabled(True)

        self.currentArtistText = QLabel("Current artist: -", self)
        self.currentArtistText.setGeometry(QRect(10, 10, 770, 30))
        self.currentArtistText.setScaledContents(False)

        self.currentSongText = QLabel("Current song: -", self)
        self.currentSongText.setGeometry(QRect(10, 25, 770, 60))
        self.currentSongText.setScaledContents(False)
        self.currentSongText.setWordWrap(True)

        self.searchedSongInfo = QLabel("Searched song: -", self)
        self.searchedSongInfo.setGeometry(QRect(10, 110, 770, 60))
        self.searchedSongInfo.setScaledContents(False)
        self.searchedSongInfo.setWordWrap(True)

        self.auto_search_checkbox = QCheckBox('Auto search lyrics?', self)
        self.auto_search_checkbox.setGeometry(QRect(515, 515, 770, 60))

        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setGeometry(QRect(10, 160, 490, 480))

        self.verLbl = QLabel("Version: 4.1", self)
        self.verLbl.setGeometry(QRect(725, 0, 100, 15))

        self.searchLyricsBtn.clicked.connect(self.search_lyrics)
        self.auto_search_checkbox.toggled.connect(self.auto_search_lyrics)

        self.searchLyricsBtn.setStyleSheet("font: 25pt")
        self.currentSongText.setStyleSheet("font: 15pt")
        self.currentArtistText.setStyleSheet("font: 15pt")
        self.searchedSongInfo.setStyleSheet("font: 15pt")
        self.auto_search_checkbox.setStyleSheet("font: 14pt")
        self.textBrowser.setStyleSheet("font: 13pt")
        self.verLbl.setStyleSheet("font: 10pt")
        self.textBrowser.setText(info_msg)

        if auto_search == 'False':
            self.searchLyricsBtn.setEnabled(True)
            self.auto_search_checkbox.setChecked(False)
        else:
            self.searchLyricsBtn.setEnabled(False)
            self.auto_search_checkbox.setChecked(True)

        last_song = sp.song()
        last_artist = sp.artist()
        self.info_updater()

    def auto_search_lyrics(self):
        global auto_search
        tree = ET.parse(settings_path)
        root = tree.getroot()
        if self.auto_search_checkbox.isChecked():
            auto_search = "True"
            root[0].text = "True"
            self.searchLyricsBtn.setEnabled(False)
            self.info_updater()
            self.search_lyrics()
        else:
            auto_search = "False"
            root[0].text = "False"
            self.searchLyricsBtn.setEnabled(True)

        tree.write(settings_path)

        print("(DEBUG) Auto search set to: " + auto_search + "\n")

    def search_lyrics(self):
        try:
            self.thread = LyricsThread()
            self.thread.terminate()
            self.textBrowser.setText(f"Searching for {sp.artist()} - {sp.song().rstrip('.')}...")
            self.thread.lyrics_data.connect(self.on_lyrics_ready)
            self.thread.song_info_data.connect(self.on_song_info_ready)
            self.thread.start()
        except sp.SpotifyNotRunning as e:
            self.textBrowser.setText(error_msg)
            self.currentSongText.setText("Current song: -")
            self.currentArtistText.setText("Current artist: -")
            print("(DEBUG) " + str(e))

    def info_updater(self):
        self.thread2 = UpdateInfo()
        self.thread2.info_data.connect(self.on_info_ready)
        self.thread2.error_data.connect(self.on_error_ready)
        self.thread2.changed_data.connect(self.on_changed_ready)
        self.thread2.start()

    def on_lyrics_ready(self, data):
        global curr_lyrics
        self.textBrowser.setText(data)
        curr_lyrics = self.textBrowser.toPlainText()

    def on_song_info_ready(self, data):
        self.searchedSongInfo.setText("Searched song: " + data)
        text_len = len(self.searchedSongInfo.text())

        if text_len > 65:
            self.searchedSongInfo.setGeometry(QRect(10, 80, 770, 60))
        else:
            self.searchedSongInfo.setGeometry(QRect(10, 110, 770, 60))

    def on_info_ready(self, data):
        global curr_song, curr_artist
        data = data.split(";data;")
        curr_song = data[0].strip()
        curr_artist = data[1].strip()

        self.currentSongText.setText("Current song: " + curr_song)
        self.currentArtistText.setText("Current artist: " + curr_artist)
        text_len = len(self.currentSongText.text())

        if text_len > 65:
            self.currentSongText.setGeometry(QRect(10, 35, 770, 60))
        else:
            self.currentSongText.setGeometry(QRect(10, 25, 770, 60))

    def on_error_ready(self, data):
        if data[0:6] != "<NOERR>" and data[-7:-1] != "<NOERR":
            self.textBrowser.setText(data)
            self.currentSongText.setText("Current song: -")
            self.currentArtistText.setText("Current artist: -")
        else:
            self.textBrowser.setText(data[7:-7])

    def on_changed_ready(self, data):
        if auto_search == "True":
            self.search_lyrics()


class LyricsThread(QThread):

    lyrics_data = pyqtSignal(object)
    song_info_data = pyqtSignal(object)

    def run(self):
        global got_error, curr_artist, curr_song

        response = request_song(curr_song, curr_artist)
        json = response.json()
        remote_song_info = None

        for hit in json['response']['hits']:
            if curr_artist.lower() in hit['result']['primary_artist']['name'].lower():
                remote_song_info = hit
                break

        if remote_song_info:
            song_url = remote_song_info['result']['url']
        else:
            song_url = "The song couldn't be found!\n(Maybe the title on Spotify differs from the one on Genius.com or " \
                       "there are no lyrics for this song."
            self.lyrics_data.emit(song_url)
            print("ERROR: Couldn't get the song url.")
            return

        self.lyrics_data.emit(scrape_song_url(song_url))
        self.song_info_data.emit(searched_song_info)
        got_error = False


class UpdateInfo(QThread):

    info_data = pyqtSignal(object)
    error_data = pyqtSignal(object)
    changed_data = pyqtSignal(object)

    def run(self):
        global last_song, last_artist, curr_artist, curr_song, got_error

        try:
            while True:
                curr_song = sp.song()
                curr_artist = sp.artist()

                if last_song != curr_song:
                    self.changed_data.emit(True)
                elif last_song == curr_song and last_artist != curr_artist:
                    self.changed_data.emit(True)

                data = curr_song + ";data;" + curr_artist

                self.info_data.emit(data)
                last_song = curr_song
                last_artist = curr_artist
                sleep(0.5)
        except sp.SpotifyNotRunning as e:
            if not got_error:
                self.error_data.emit("<NOERR>" + curr_lyrics + "<NOERR>")
            got_error = True
            if curr_lyrics == info_msg:
                print("(DEBUG) " + str(e))
                self.error_data.emit(error_msg)
            sleep(0.5)
            self.run()


def request_song(song_title, artist_name):
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + token}
    search_url = base_url + '/search'

    final = False
    if "-" in song_title:  # e.g *Title*: "Close - Brooks Remix" | Remove the "Brooks Remix" part of the title
        new_title = song_title.split("-")
        song_title = new_title[0].strip()
    for word in excluded_words:
        if word in song_title:
            new_title = song_title.split(word)
            song_title = new_title[0].strip()

    final_check = song_title.split()  # Final check for songs like: Parah Dice - Hot (Imanbek Remix) where the remix's
    for word in final_check:          # author is added in the song's title: *(Imanbek Remix)*
        if word[0] == "(":
            final_check.remove(word)
            final = True
        elif word[0:5] == "Remix" or word[0:5] == "remix":
            final_check.remove(word)
            final = True

    if final:
        song_title = ""
        for i, ele in enumerate(final_check):
            if i < len(final_check) - 1:
                song_title += ele + " "
            else:
                song_title += ele

    data = {'q': song_title + ' ' + artist_name}
    print("(DEBUG) SEARCH DATA: " + str(data))
    response = requests.get(search_url, data=data, headers=headers)

    return response


def scrape_song_url(url):
    global searched_song_info
    try:
        page = requests.get(url)
        html = BeautifulSoup(page.text, 'html.parser')
        old_div = html.find('div', class_="lyrics")
        new_div = html.find('div', class_="SongPageGrid-sc-1vi6xda-0 DGVcp Lyrics__Root-sc-1ynbvzw-0 jvlKWy")
        if old_div:
            lyrics = old_div.get_text()
        elif new_div:
            # Clean the lyrics since get_text() fails to convert "</br/>"
            lyrics = str(new_div)
            lyrics = lyrics.replace('<br/>', '\n')
            lyrics = re.sub(r'(\<.*?\>)', '', lyrics)

        song_info = html.find('title').get_text()

        song_info = song_info.split("Lyrics |")
        song_info = song_info[0].strip()
        searched_song_info = song_info

        lyrics = lyrics.strip()
        return lyrics
    except Exception as e:
        print(f"(ERROR) FATAL ERROR! (Could not acquire lyrics for this song: {url}) -> {str(e)}")
        searched_song_info = "ERROR"
        return "There was an error getting lyrics for this song from Genius. \n" \
               "It's probably a problem with the Genius website for this song.\n" \
               "Sorry!"


def project_website():
    webbrowser.open_new_tab("https://whiteaspect.wixsite.com/aspect")

def close_app():
    try:
        LyricsThread().terminate()
        UpdateInfo().terminate()
    except:
        print("(ERROR) COULD NOT TERMINATE THREADS!")
    sys.exit(0)


if __name__ == "__main__":
    import sys
    app = QApplication([])

    MainWindow = Window()
    MainWindow.show()

    sys.exit(app.exec_())
