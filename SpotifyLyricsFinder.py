# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal, QThread, QRect
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLabel, QTextBrowser, QMenuBar, QMenu, \
    QStatusBar, QAction
import requests
from bs4 import BeautifulSoup
from SwSpotify import spotify as sp

excluded_words = ['(feat', 'ft.', 'remix', 'Remix', 'REMIX']
token = 'HERE GOES YOUR genius.com API TOKEN'  # API TOKEN REQUIRED FOR THE APP TO WORK!


class UiPanel(QWidget):  # All the GUI parts
    def __init__(self, parent):
        QWidget.__init__(self)
        self.Parent = parent

        self.searchLyricsBtn = QPushButton("Search for lyrics!", self)
        self.searchLyricsBtn.setGeometry(QRect(655, 485, 135, 71))
        self.getCurrInfoBtn = QPushButton("Get current \nsong's info", self)
        self.getCurrInfoBtn.setGeometry(QRect(513, 485, 135, 71))
        self.currentArtistText = QLabel("Current artist: -", self)
        self.currentArtistText.setGeometry(QRect(10, 10, 770, 30))
        self.currentArtistText.setScaledContents(False)
        self.currentSongText = QLabel("Current song: -", self)
        self.currentSongText.setGeometry(QRect(10, 40, 770, 30))
        self.currentSongText.setScaledContents(False)
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setGeometry(QRect(10, 75, 490, 480))

        self.searchLyricsBtn.clicked.connect(self.search_lyrics)
        self.getCurrInfoBtn.clicked.connect(self.get_current_info)

        self.getCurrInfoBtn.setStyleSheet("font: 12pt Cosmic Sans MS")
        self.searchLyricsBtn.setStyleSheet("font: 12pt Cosmic Sans MS")
        self.currentSongText.setStyleSheet("font: 15pt Cosmic Sans MS")
        self.currentArtistText.setStyleSheet("font: 15pt Cosmic Sans MS")
        self.textBrowser.setStyleSheet("font: 13pt Cosmic Sans MS")
        self.textBrowser.setText("Your lyrics will show up here!")

        self.get_current_info()

    def get_current_info(self):  # Get current artist and song title that is playing
        curr_song = sp.song()
        curr_artist = sp.artist()

        self.currentSongText.setText("Current song: " + curr_song)
        self.currentArtistText.setText("Current artist: " + curr_artist)

    def search_lyrics(self):  # Start the thread for searching the lyrics
        self.textBrowser.setText(f"Searching for {sp.artist()} - {sp.song().rstrip('.')}...")
        self.get_current_info()
        self.thread = LyricsThread()
        self.thread.lyrics_data.connect(self.on_lyrics_ready)
        self.thread.start()

    def on_lyrics_ready(self, data):  # Display the lyrics in the app
        self.textBrowser.setText(data)


class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setFixedSize(800, 600)
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
        self.setStatusBar(self.statusbar)
        self.actionClose = QAction(self)
        self.actionClose.setText("Close")
        self.menuFile.addAction(self.actionClose)
        self.menubar.addAction(self.menuFile.menuAction())

        self.actionClose.triggered.connect(close_app)


class LyricsThread(QThread):  # Lyrics searching thread

    lyrics_data = pyqtSignal(object)

    def run(self):
        response = request_song(sp.song(), sp.artist())
        json = response.json()
        remote_song_info = None

        for hit in json['response']['hits']:
            if sp.artist().lower() in hit['result']['primary_artist']['name'].lower():
                remote_song_info = hit
                break

        if remote_song_info:
            song_url = remote_song_info['result']['url']
        else:
            song_url = "The song couldn't be found!"
            self.lyrics_data.emit(song_url)
            print("ERROR: Couldn't get the song url.")
            return

        scrap_song_url(song_url)
        self.lyrics_data.emit(scrap_song_url(song_url))


def request_song(song_title, artist_name):  # Prepare song's artist and title to request the data from the website
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + token}
    search_url = base_url + '/search'

    if "-" in song_title:  # e.g *Title*: "Close - Brooks Remix" | Remove the "Brooks Remix" part of the title
        new_title = song_title.split("-")
        song_title = new_title[0].strip()
    else:
        for word in excluded_words:  # Remove the words from the excluded_words list to make sure app finds the lyrics
            if word in song_title:
                new_title = song_title.split(word)
                song_title = new_title[0].strip()

    data = {'q': song_title + ' ' + artist_name}
    print("(DEBUG) SEARCH DATA: " + str(data))
    response = requests.get(search_url, data=data, headers=headers)

    return response


def scrap_song_url(url):  # Get the lyrics from the website
    page = requests.get(url)
    html = BeautifulSoup(page.text, 'html.parser')
    lyrics = html.find('div', class_='lyrics').get_text()

    lyrics = lyrics.strip()
    return lyrics


def close_app():  # App closing function
    sys.exit(0)


if __name__ == "__main__":
    import sys
    app = QApplication([])

    MainWindow = Window()
    MainWindow.show()

    sys.exit(app.exec_())
