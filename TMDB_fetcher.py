#! /usr/bin/python
# -*- coding: utf-8 -*-
"""TMDB_fetcher.py script.

Cet outil permet de naviguer à travers une arborescence de répertoires contenant des fichiers films.
L'outil interroge la base de donnée de cinéma TMDB et établit pour chaque film une noté d'informations.
La note aura le même nom que le film, avec une extensions  _imdb.txt . 
Le film sera renommé en fonction du titre exact trouvé dans la base et de l'année de sa sortie.
L'affiche correspondant au film sera également téléchargée.
Les titres et notes d'information sont en Français.
Un catalogue de tous les films trouvés  sera établi à la racine du dossier (MOVIE_CATALOG.TXT). 

Important : Une clé doit avoir été obtenue du site TMDB en créant un compte sur https://www.themoviedb.org/account/signup.

En cas d'ajout de nouveaux films, l'outil peut être relancé, les films déjà traités ne seront pas modifiés, seuls les nouveaux films seront recherchés.
On peut également effacter toutes les informations et recommencer avec l'option --cleanup.
Enfin, on peut ne chercher les informations que pour un seul fichier avec l'option --file 
(dans ce cas, les informations existantes seront remplacées pour ce film).
        
This tool allows for walking through a directory tree containing movie files and to query the TMDB movie database
in order to establish a note describing each found movie.
The note will have the same name as the movie file, with _imdb.txt extension.
A catalog is established listing all the found files (MOVIE_CATALOG.TXT).

Note : A key must be obtained by registering an account at https://www.themoviedb.org/account/signup .
       The key must be provided as a parameter.
       La clé doit être fournie en paramètre.
       
Note 2 : Si on souhaite éviter certains répertoires (séries TV par exemple), il suffit
       d'ajouter "_NOTMDB" dans le nom du répertoire.
       De même, pour les partie2 ou CD2, on peut ajouter _NOTMDB au nom pour passer.
       
The tool can be relaunched in case of new files addition, only new files will be handled.
It is possible to delete all informations with the --cleanup otion.
A single file can also be handled using option --file (replacing previous informations).


Copyright Christophe Mineau - www.labellenote.fr
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License


Usage:
    TMDB_fetcher.py <rootDirPath> --key=<TMDB_KEY>   [--verbose] 
    TMDB_fetcher.py <rootDirPath> --key=<TMDB_KEY>   --file=<filePath> [--verbose] 
    TMDB_fetcher.py <rootDirPath> --cleanup [--verbose] 
    TMDB_fetcher.py  (-h | --help)

Options:
   -h --help               Get help.
  --version                Get this program version.
  --key=<key>              Key provided by TMDBapi.com, see http://www.TMDBapi.com/apikey.aspx
  --file="<path to file>"  To handle a single file.
  --verbose                Prints all informations got from TMDB  
  --cleanup                Removes all files generated by this tool.
  
  
Example:
  python TMDB_fetcher.py "E:\Videos" -k=abcdef 
  python TMDB_fetcher.py "D:\" -k=abcdef --file="D:\Avatar.mp4"
  python TMDB_fetcher.py "E:\Videos" --cleanup
  
"""
# TMDB API, see : https://pypi.org/project/tmdbv3api/
# see the json schemas here :  https://developers.themoviedb.org/3/movies/get-movie-details

from tmdbv3api import TMDb  # $ pip install tmdbv3api
TMDB = TMDb()
from tmdbv3api import Movie
MOVIE = Movie()

import json
import argparse
from docopt import docopt  # pip install docopt
import os
import sys
import re
import textwrap
import logging
import datetime
import wget # pip install wget


VERSION = 1.0
LOG_FILE = "__TMDB_FETCHER.LOG"
CATALOG = "___CATALOGUE_FILMS.TXT"
SHEETS = "___FICHES_FILMS.TXT"
SHEET_SUFFIX = '_tmdb.txt'
POSTER_SUFFIX = '_tmdb'
DO_NOT_INDEX = '_NOTMDB'



class dbFile:
    "generic catalog file, class to be inherited"
    SEPARATOR = '-'*40+'\n'
    def __init__(self, f):
        self.filePath = f
        self.fileTxt = ''
        
    def txtFormat(self, mv): 
        "to be overwritten"
        return mv    
        
    def addFilm(self, mv):
        self.fileTxt += self.txtFormat(mv)
        self.nbFilms += 1
    
    def writeFile(self):
        global LOGGER
        global VERSION
        with open(self.filePath, "w", encoding="utf-8") as fh:
            fh.write("Fichier édité le {} par TMDB_fetcher.py version {}.\n".format(datetime.datetime.now(), VERSION))
            fh.write("Copyright C.Mineau - TMDB_fetcher.py est disponible ici : https://github.com/ChristopheMineau/TMDB_fetcher-French.\n")
            fh.write("La base contient à cette date {} films.\n\n".format(self.nbFilms))
            fh.write(self.fileTxt)
            LOGGER.debug("Fichier créé : '{}'".format(self.filePath))
        print("Consulter le fichier : '{}'".format(self.filePath))
        
    def readFile(self):
        global LOGGER
        if not os.path.isfile(self.filePath):
            LOGGER.error("Fichier non trouvé : '{}'".format(self.filePath))
            return False
        
        with open(self.filePath, "r", encoding="utf8") as fh:
            self.fileTxt = fh.read()
            LOGGER.debug("Lecture fichier : '{}'".format(self.filePath))
        #fileListExp = r"^La base contient à cette date (\d+) films.\n\n([\s\S]*)"
        fileListExp = r"cette date (\d+) films.\n\n([\s\S]*)"
        m = re.search(fileListExp, self.fileTxt, re.MULTILINE)
        if m:
            self.nbFilms = int(m.group(1))
            self.fileTxt = m.group(2)
        else:
            LOGGER.error("Erreur: format incorrect pour le fichier : '{}'".format(self.filePath))
            return False
        return True
    
class Catalog(dbFile):
    def __init__(self, f):
        dbFile.__init__(self, f)
        self. nbFilms = 0
        
    def txtFormat(self, mv): 
        "mv is of class Film"
        return "Titre: '{}'    --- Année: '{}'    --- Fiche: {}  --- {}  \n".format(mv.filmName, mv.filmYear, "oui" if mv.note else "non", mv.filePath)
    
    def removeFilm(self, mv):
        """ used while updating the catalog : remove if exist the film entry"""
        lines = self.fileTxt.rstrip().split('\n')     # removes trailing newline before splitting
        searchExp = "Titre: '{}'    ---".format(mv.filmName)
        for l in lines:
            if re.search(searchExp, l):
                lines.remove(l)
                break
        self.fileTxt = '\n'.join(lines)+'\n'
        self.nbFilms = len(lines)
        
class NoteFile(dbFile):
    def __init__(self, f):
        dbFile.__init__(self, f)
        self. nbFilms = 0
    
    def txtFormat(self, mv):
        "mv is of class Film"
        if mv.note:
            note = mv.note
        else:
            note = "Chemin : {}\nAucune info sur TMDB.".format(mv.filePath)
        return "{sep}{}\n{sep}\n\n".format(note, sep=dbFile.SEPARATOR)
        
    def removeFilm(self, mv):
        """ used while updating the Notes file : remove if exist the film entry"""
        lines = self.fileTxt.split('\n')     # removes trailing newline before splitting
        searchExp =  re.escape("Chemin : {}".format(mv.filePath))   
        sepExp = '^' + dbFile.SEPARATOR[:10]
        # look for the movie record line beginning and line end
        prevSepIdx = None
        nextSepIdx = None
        recordFound = False
        for idx, l in enumerate(lines):
            if re.search(sepExp, l):
                if recordFound:          # we are inside the searched record
                    nextSepIdx = idx + 2 # include the 2 newlines after line separator
                    break
                else:
                    prevSepIdx = idx     # this a beginning of a record
                    continue
            if re.search(searchExp, l):  # found the record
                recordFound = True
        # delete the record if found
        if recordFound and prevSepIdx and nextSepIdx:
            del lines[prevSepIdx : nextSepIdx+1]
            self.nbFilms -= 1
        # rejoin the lines         
        self.fileTxt = '\n'.join(lines)
        
class Film:
    def __init__(self, f, dontKeepIfExist):
        global DEBUG
        global LOGGER
        self.filePath = f 
        self.fileDir = os.path.dirname(f)
        self.filmName , self.filmYear, self.filmExtension = Film.getFilmNameAndYearFromPath(f)
        sheetPath = Film.doesSheetAlreadyExist(f, dontKeepIfExist)
        if sheetPath: 
            self.initFromExistingSheet(sheetPath)
        else:
            self.poster = None  
            TMDBSearchEnd = False
            while not TMDBSearchEnd:
                self.queryTMDB()
                TMDBSearchEnd = True if self.tmdbId else self.proposeAlternative()
            self.buildNote()
            self.writeNote()
            if self.poster:
                self.downloadPoster()
                
    def initFromExistingSheet(self, sheetPath):
        with open(sheetPath, "r", encoding="utf-8") as f:
            self.note = f.read()
        posterExp = r"Affiche : (.+)$"
        m = re.search(posterExp, self.note, re.MULTILINE)
        if m:
            self.poster = m.group(1)
        else:    
            self.poster = None
    
    @classmethod    
    def isMovie(cls,f, p):
        global DO_NOT_INDEX
        if "RECYCLE.BIN" in p:    # filters the trash on Windows
            return False
        if DO_NOT_INDEX in p:    # filters explicitely what must not be indexed
            return False
        if DO_NOT_INDEX in f:    # filters explicitely what must not be indexed
            return False
        filename, file_extension = os.path.splitext(f)
        return file_extension.lower() in {'.avi', '.mp4', '.mpg', '.mpeg'}
    
    @classmethod
    def doesSheetAlreadyExist(cls, f, dontKeepIfExist):
        """ checks if the sheet and poster already exist (update case)"""
        global SHEET_SUFFIX
        global POSTER_SUFFIX
        global LOGGER
        filePathAndName, fileExtension = os.path.splitext(f)
        sheetPath =  filePathAndName + SHEET_SUFFIX 
        
        if os.path.isfile(sheetPath):
            LOGGER.info("La fiche existe déjà pour le film  : '{}'".format(f))
            if dontKeepIfExist:
                try:
                    os.remove(sheetPath)
                    LOGGER.info("Fichier supprimé : '{}'".format(sheetPath))
                except:
                    LOGGER.warn("Impossible de supprimer : '{}'".format(sheetPath))
                sheetPath = None
        else:
            sheetPath = None
        
        return sheetPath

    
    @classmethod    
    def getFilmNameAndYearFromPath(cls, p):
        global LOGGER
        baseName = os.path.basename(p)
        fileName, fileExtension = os.path.splitext(baseName)
        yearExp = "[\s\.-]*\(?(\d\d\d\d)\)?\s*$"
        m = re.search(yearExp, fileName)
        if m:
            year =  m.group(1)
            filmName = fileName[0:m.start()]
        else:
            year = None
            filmName = fileName
        filmName = filmName.replace('.',' ')
        filmName = filmName.replace('_',' ')
        LOGGER.info("\n\n"+'-'*80+"\n{} ==> Titre='{}' année='{}'".format(p, filmName , year)) 
        return filmName, year, fileExtension 
    
    @classmethod    
    def getYearFromTmdbDate(cls, d):
        return d.split('-')[0]
    
    def queryTMDB(self):
        """Queries TMDB and tries to narrow the list returned by date
        sets tmdbId if found else possibleList"""
        global LOGGER
        self.tmdbId = None
        self.possibleList = []
        print("Recherche d'informations sur le film '{}'.".format(self.filmName))
        pg = 1
        filmList = []
        searchEnd = False
        while not searchEnd and pg<=4: 
            pageList =  MOVIE.search(self.filmName, page=pg)
            filmList += pageList
            if len(pageList) != 20:
                searchEnd = True
            else:
                pg += 1
        LOGGER.info("TMDB a retourné {} possibilités : {}".format(len(filmList), [f.title+'-'+f.release_date for f in filmList]))
        # check if in the list something matches with the file Year
        if self.filmYear:
            foundCount = 0
            for f in filmList:
                if Film.getYearFromTmdbDate(f.release_date)==self.filmYear and self.filmName.strip().lower()==f.title.strip().lower():
                    foundCount += 1
                    selectedFilm = f
            if foundCount == 1:  # If only one film with matching year, consider it is it
                LOGGER.info("Le titre et l'année correspondent.")
                self.tmdbId = selectedFilm.id
                self.renameFilm("{} - {}".format(selectedFilm.title, Film.getYearFromTmdbDate(selectedFilm.release_date)))
                return  
            else:
                self.tmdbId = None
        else:
            if len(filmList)==1:
                selectedFilm = filmList[0]
                self.tmdbId = selectedFilm.id
                self.renameFilm("{} - {}".format(selectedFilm.title, Film.getYearFromTmdbDate(selectedFilm.release_date)))
                return
            else:
                self.tmdbId = None
        self.possibleList = filmList  # otherwise returns the list, possibly empty list
             

    def proposeAlternative(self):
        """ In case 0 or several films compete, ask the operator for his choice"""
        global LOGGER
        TMDBSearchEnd = True
        
        def correctAnswer(limit, answer):
            try:
                answer=int(answer)
            except:
                return False
            return True if answer>=0 and answer<=limit else False
        
        if len(self.possibleList)==0:  # No choice from TMDB
            return self.proposeRenaming()
        
        LOGGER.debug("Liste de choix proposée pour le film '{}'".format(self.filmName))
        
        print("Plusieurs possibilités pour le film '{}'\nRenommer le film : \n ".format(self.filePath), end='')
        choice=[ "\t{i} : {t} - {y} - {ot} - {ov}".format(i=indice, 
                                                          t=f.title, 
                                                          y=f.release_date,
                                                          ot=f.original_title,
                                                          ov=f.overview[:80]) for indice, f in enumerate(self.possibleList)]
        choice.append("\t{} : Autre titre".format(len(choice)))
        choice.append("\t{} : Passer".format(len(choice)))
        choice.append("\t{} : Ignorer et ne plus demander à l'avenir.".format(len(choice)))
        for c in choice:
            print(c)
            LOGGER.debug("{}'".format(c))
        satisfyingAnswer = False
        while not satisfyingAnswer:
            print("\tVotre choix ? (0<{}) : ".format(len(choice)-1), end='')
            r = input()
            if correctAnswer(len(choice)-1, r):
                satisfyingAnswer = True
            else:
                LOGGER.debug("Entrée incorrecte '{}'".format(r))                
        LOGGER.info("Choix retenu '{}'".format(r))  
        if int(r)==len(choice)-1:     # Ignorer
            fileName, fileExtension = os.path.splitext(os.path.basename(self.filePath))
            ignoreName = fileName + DO_NOT_INDEX
            self.renameFilm(ignoreName)
            TMDBSearchEnd = True
            self.tmdbId = None  
        elif int(r)==len(choice)-2:     # Passer
            TMDBSearchEnd = True
            self.tmdbId = None
        elif int(r)==len(choice)-3:  # Autre
            TMDBSearchEnd = self.proposeRenaming(elseChoice=True)
        else:
            TMDBSearchEnd = True  # Choix parmi les films proposés
            selectedFilm = self.possibleList[int(r)]
            self.tmdbId = selectedFilm.id
            self.renameFilm("{} - {}".format(selectedFilm.title, Film.getYearFromTmdbDate(selectedFilm.release_date))) # Align file name with TMDB name
                       
        return TMDBSearchEnd        
        

    def proposeRenaming(self, elseChoice=False):
        """ In case no idea, ask the operator for a renaming"""
        global LOGGER
        satisfyingAnswer = False
        TMDBSearchEnd = True
        
        LOGGER.debug("Renommage proposé pour le film '{}'".format(self.filmName))
        if elseChoice:
            r='o'
        else:
            while not satisfyingAnswer:
                print("La base de donnée TMDB ne connaît pas le fichier '{}'\nVoulez vous le renommer (O/N) ou l'ignorer pour qu'il ne soit plus proposé (I) ? : ".format(self.filePath), end='')
                r = input().lower()
                satisfyingAnswer = True if r in ('o', 'n','i') else False
            
        if r=="o":
            LOGGER.debug("  Nouveau nom :'{}'".format(r))
            satisfyingAnswer = False
            while not satisfyingAnswer:
                print("Proposez un nouveau nom pour le film '{}' :".format(self.filmName))
                print("Conseil: Pour plus de précision, il est possible d'ajouter la date de sortie à la fin du nom, exemple : 'Avatar-2009'.\nNouveau nom : ", end='')
                r = input()
                satisfyingAnswer = True if r else False
            TMDBSearchEnd = False if self.renameFilm(r) else True
        elif r=='i':
            LOGGER.debug("  Ignorer ce fichier.")
            fileName, fileExtension = os.path.splitext(os.path.basename(self.filePath))
            ignoreName = fileName + DO_NOT_INDEX
            self.renameFilm(ignoreName)
            TMDBSearchEnd = True
            self.tmdbId = None
            
        else:
            LOGGER.debug("  PAS de nouveau nom.")
            TMDBSearchEnd = True
            self.tmdbId = None
            
        return TMDBSearchEnd
                
    def renameFilm(self, r):
        global LOGGER
        
        def askUser():
            correctAnswer = False
            print("Erreur de renommage du fichier {}\nS'il est en cours de lecture, veuillez le fermer.\nPeut-être qu'un fichier existe déjà du même nom.".format(self.filePath))
            while not correctAnswer:
                print("Ré-essayer ? (O/N) : ", end='')
                r = input().lower()
                correctAnswer = r in {'o', 'n'}
            return r == 'o'
                  
        # sanitization
        r = r.replace('<', ' ')
        r = r.replace('>', ' ')
        r = r.replace(':', ' ')
        r = r.replace('"', ' ')
        r = r.replace('/', ' ')
        r = r.replace('\\', ' ')
        r = r.replace('|', ' ')
        r = r.replace('?', ' ')
        r = r.replace('*', ' ')
        newFilePath = os.path.join(self.fileDir, r + self.filmExtension)
        if newFilePath != self.filePath:
            LOGGER.info("Renommage '{}' => '{}'".format(self.filePath, newFilePath))
            tryRenaming = True
            while tryRenaming:
                try:
                    os.rename(self.filePath, newFilePath)
                    tryRenaming = False
                except IOError as e:
                    tryRenaming = askUser()
                    if not tryRenaming:
                        LOGGER.error("Erreur en renommant {}, exception : {}".format(r, e.strerror))
                        return False
            self.filePath = newFilePath
            self.filmName , self.filmYear, self.filmExtension = Film.getFilmNameAndYearFromPath(newFilePath) 
        return True    
            
    def buildNote(self):
        global LOGGER
       
        if self.tmdbId:
            details = MOVIE.details(self.tmdbId)
            credits = MOVIE.credits(self.tmdbId)
            actorsList =  [a['name'] for a in credits.cast]
            genreList = [g['name'] for g in details.genres]
            directorList = [d['name'] for d in credits.crew if d['job']=="Director"]
            writersList = [d['name'] for d in credits.crew if d['job']=="Screenplay"]
            music = [d['name'] for d in credits.crew if "Music" in d['job']]
            pays = [p['name'] for p in details.production_countries]
            self.poster = "http://image.tmdb.org/t/p/w400" + details.poster_path if details.poster_path else None
            self.note = "Titre : {}\n".format (details.title)
            self.note += "Chemin : {}\n".format (self.filePath)    
            self.note += "Année : {}\n".format (Film.getYearFromTmdbDate(details.release_date))
            self.note += "Acteurs : {}\n".format (actorsList)
            self.note += "Genre : {}\n".format (genreList)
            self.note += "Pays : {}\n".format (pays)
            self.note += "Affiche : {}\n".format (self.poster)
            self.note += "Durée (mn) : {}\n".format (details.runtime)
            self.note += "Metteur en scène : {}\n".format (directorList)
            self.note += "Auteur : {}\n".format (writersList) 
            self.note += "Musique : {}\n".format (music) 
            self.note += "Synopsis : {}".format (textwrap.fill(details.overview,80))
        else:
            self.note = None
        LOGGER.info(self.note)
        
    def writeNote(self):
        global LOGGER
        global SHEET_SUFFIX
        if self.note:
            dirName =  os.path.dirname(self.filePath)
            baseName = os.path.basename(self.filePath)
            fileName, fileExtension = os.path.splitext(baseName)
            noteFileName = os.path.join(dirName, fileName + SHEET_SUFFIX)
            LOGGER.info("Ecriture fiche  : {}".format(noteFileName))  
            with open(noteFileName, "w", encoding="utf-8") as f:
                    f.write(self.note)
        else:
            LOGGER.info("Aucune info pour le film : {}".format(self.filmName))  
       
    def downloadPoster(self):
        global POSTER_SUFFIX
        global LOGGER
        dirName =  os.path.dirname(self.filePath)
        baseName = os.path.basename(self.filePath)
        fileName, fileExt = os.path.splitext(baseName)
        posterName, posterExt = os.path.splitext(self.poster)
        posterPath = os.path.join(dirName, fileName + POSTER_SUFFIX + posterExt)
        if os.path.isfile(posterPath):
            LOGGER.info("Affiche existe déjà : {}".format(posterPath))
            try:
                os.remove(posterPath)
                LOGGER.info("Affiche supprimée : {}".format(posterPath))
            except:
                LOGGER.warn("Impossible de supprimer : {}".format(posterPath))
        try:
            downloadName = wget.download(self.poster, out=posterPath)
            LOGGER.info("Affiche téléchargée : {}".format(posterPath))
        except:
            LOGGER.warn("Echec de téléchargement: {}".format(self.poster)) 
            return
                

    
class MovieDB:
    " Small DB holding the found informations and able to make catalogus"
    def __init__(self, path): 
        global MOVIE_CATALOG
        global MOVIE_SHEETS
        self.rootPath = path
        self.movieDB = []
        self.movieCatalog = Catalog(os.path.join(self.rootPath, MOVIE_CATALOG))
        self.noteFile = NoteFile(os.path.join(self.rootPath, MOVIE_SHEETS)) 
        
    def lookForMovies(self):
        for (dirpath, dirnames, filenames) in os.walk(self.rootPath):
            for filename in filenames:
                if Film.isMovie(filename, dirpath): 
                    self.handleMovie(os.path.join(dirpath, filename))
                    
    def handleMovie(self, filepath, dontKeepIfExist = False):
        self.movieDB.append(Film(filepath, dontKeepIfExist))
                    
    def doBuildMovieNotesFile(self):
        "makes a single file gathering all the notes for the found films, instead of plenty of small notes here and there"
        for mv in self.movieDB:
            self.noteFile.addFilm(mv)
        self.noteFile.writeFile()
    
    def updateMovieNotesFile(self):
        """updates the existing sheets with the added film
           In this case the db contains only 1 film"""
        if self.noteFile.readFile():
           self.noteFile.removeFilm(self.movieDB[0])
           self.noteFile.addFilm(self.movieDB[0])
           self.noteFile.writeFile()
    
    def doBuildCatalog(self):
        "makes a catalog listing the found files"
        for mv in self.movieDB:
            self.movieCatalog.addFilm(mv)
        self.movieCatalog.writeFile()
        
    def updateCatalog(self):
        """updates the existing catalog with the added film
            In this case the db contains only 1 film"""
        if self.movieCatalog.readFile():
           self.movieCatalog.removeFilm(self.movieDB[0])
           self.movieCatalog.addFilm(self.movieDB[0])
           self.movieCatalog.writeFile()


def doCleanup(p):
    "Removes all the files generated by this tool"   
    global LOGGER
    global SHEET_SUFFIX
    global POSTER_SUFFIX
    global CATALOG
    global SHEETS
    
    def isNote(f):
        return True if SHEET_SUFFIX in f else False
    
    def isCatalogue(f):
        return True if CATALOG in f else False
    
    def isSingleNote(f):
        return True if SHEETS in f else False
    
    def isPoster(f):
        return True if POSTER_SUFFIX in f else False
    
    for (dirpath, dirnames, filenames) in os.walk(p):
        for filename in filenames:
            if isNote(filename) or isCatalogue(filename) or isSingleNote(filename) or isPoster(filename): 
                filepath = os.path.join(dirpath, filename)
                os.remove(filepath)
                LOGGER.debug("Fichier supprimé : '{}'".format(filepath))
                
                
                


if __name__ == "__main__":

    # __doc__ contains the module docstring
    # docopt lib manages the arguments and the manager is built upon the help string provided (posix style). Here we give the docstring
    

    
    ## Manage arguments ## 
    arguments = docopt(__doc__, version=VERSION)
    #print(arguments)
    try:
        DIRPATH = arguments['<rootDirPath>']
        VERBOSE = True if arguments['--verbose'] else False
        KEY = arguments['--key']
        FILE = arguments['--file']
        CLEANUP = True if arguments['--cleanup'] else False
    except:
        print("ERROR: Incorrect parameters, use --help.")
        exit(1)
        
    #exit(0)
        
    ## Logging Capacity ##
    # create logger
    LOGGER = logging.getLogger("TMDB_fetcher.py")
    LOGGER.propagate = False
    LOGGER.setLevel(logging.DEBUG)
    # create console handler and set level 
    ch = logging.StreamHandler()
    if VERBOSE:
        ch.setLevel(logging.INFO)
    else:
        ch.setLevel(logging.WARN)
    # create a file handler and set level 
    fh = logging.FileHandler(os.path.join(DIRPATH, LOG_FILE), encoding ="utf-8", mode='w')
    fh.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to handlers
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    # add handlers to logger
    LOGGER.addHandler(ch)
    LOGGER.addHandler(fh)
    # start of logging session
    LOGGER.info("{} - TMDB_fetcher.py - {} - by C.Mineau".format(datetime.datetime.now(), VERSION))
    
    if CLEANUP:
        doCleanup(DIRPATH)
    else:
    
        TMDB.api_key = KEY
        TMDB.language = 'fr'
        TMDB.debug = False
        
        MOVIE_CATALOG = os.path.join(DIRPATH, CATALOG)
        MOVIE_SHEETS = os.path.join(DIRPATH, SHEETS)
        
        movieDB = MovieDB(DIRPATH)
        
        if FILE:   # Only one file has to be handled, no need to walk through everything
            filename = os.path.basename(FILE)
            dirpath = os.path.dirname(FILE)
            if os.path.isfile(FILE) and Film.isMovie(filename, dirpath): 
                movieDB.handleMovie(FILE, dontKeepIfExist=True)
                movieDB.updateCatalog()
                movieDB.updateMovieNotesFile()
            else:
                LOGGER.error("Le fichier {} n'existe pas ou n'est pas un film.".format(FILE))
        else:      # walk through the Dir tree to find movies
            movieDB.lookForMovies()
            LOGGER.info("\n\n")
            movieDB.doBuildCatalog()
            movieDB.doBuildMovieNotesFile()
    
    LOGGER.info("{} - Fin de traitement TMDB_fetcher.py ".format(datetime.datetime.now()))
    print("\nFin de traitement TMDB_fetcher.py ")
    
    
