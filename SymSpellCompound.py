import copy
import re
import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG)

class dictionaryItem:
  def __init__(self):
    self.suggestions = list()
    self.count = 0

class suggestItem:
  def __init__(self):
    self.term = ''
    self.distance = 0
    self.count = 0

  def Equals (self, obj):
    return self.term == obj.term

  def ShallowCopy (self):
    return copy.copy(self)

  def __getitem__ (self, key):
    return self


class SymSpell:
  def __init__ (self):
    self.enableCompoundCheck = True
    self.editDistanceMax = 2
    self.verbose = 0

    self.dictionary = dict()
    self.wordlist = list()
    self.itemlist = list()

    self.maxlength = 0

    self.LoadDictionary("wordfrequency_en.txt", "", 0, 1);
    # self.CreateDictionary('big.txt', '')

  def parseWords (self, text):
    regex = r"\w+"
    text = text.lower()
    matches = re.findall(regex, text)
    return matches

  def CreateDictionaryEntry (self, key, language, count):
    countThreshold = 1
    countPrevious = 0
    result = False

    valueo = self.dictionary.get(language + key)
    if valueo is not None:
      if (valueo >= 0):
        tmp = valueo
        value = dictionaryItem()
        value.suggestions.append(tmp)
        self.itemlist.append(value)
        self.dictionary[language + key] = -len(self.itemlist)
      else:
        value = self.itemlist[-valueo - 1]
      countPrevious = value.count
      value.count = min(sys.maxsize, value.count + count)
    else:
      value = dictionaryItem()
      value.count = count
      self.itemlist.append(value)
      self.dictionary[language + key] = -len(self.itemlist);
      if len(key) > self.maxlength:
        self.maxlength = len(key)

    if ((value.count >= countThreshold) and (countPrevious < countThreshold)):
      self.wordlist.append(key)
      keyint = len(self.wordlist) - 1
      result = True

      for delete in self.Edits(key, 0, set()):
        value2 = self.dictionary.get(language + delete)
        if value2 is not None:
          if (value2 >= 0):
            di = dictionaryItem()
            di.suggestions.append(value2)
            self.itemlist.append(di)
            self.dictionary[language + delete] = -len(self.itemlist)
            if keyint not in di.suggestions:
              self.AddLowestDistance(di, key, keyint, delete)

          else:
            di = self.itemlist[-value2 - 1];
            if keyint not in di.suggestions:
              self.AddLowestDistance(di, key, keyint, delete)

        else:
          self.dictionary[language + delete] = keyint
    return result

  def Edits (self, word, editDistance, deletes):
    editDistance += 1
    if (len(word) > 1):
      for i in range(0, len(word)):
        delete = word[:i] + word[i+1:]
        if delete not in deletes:
          deletes.add(delete)
          if editDistance < self.editDistanceMax:
            self.Edits(delete, editDistance, deletes)

    return deletes

  def AddLowestDistance (self, item, suggestion, suggestionint, delete):
    if (self.verbose < 2 and
        len(item.suggestions) > 0 and
        len(self.wordlist[item.suggestions[0]]) - len(delete) > len(suggestion) - len(delete)
        ):
      item.suggestions = []
    if (len(item.suggestions) == 0 or
        len(self.wordlist[item.suggestions[0]]) -len(delete) >= len(suggestion) - len(delete)
        ):
      item.suggestions.append(suggestionint)


  def LoadDictionary (self, corpus, language, termIndex, countIndex):
    if not os.path.isfile(corpus):
      raise Exception('File not found: {}'.format(corpus))

    logging.info('Creating dictionary ...')
    wordCount = 0

    with open(corpus) as f:
      lines = f.readlines()
      for line in lines:
        lineParts = line.split()
        if len(lineParts) >= 2:
          key = lineParts[termIndex]
          count = int(lineParts[countIndex])
          if self.CreateDictionaryEntry(key, language, min(sys.maxsize, count)):
            wordCount += 1

  def CreateDictionary (self, corpus, language):
    if not os.path.isfile(corpus):
      raise Exception('File not found: {}'.format(corpus))

    logging.info('Creating dictionary ...')
    wordCount = 0
    with open(corpus) as f:
      lines = f.readlines()
      for line in lines:
        for key in self.parseWords(line):
          if self.CreateDictionaryEntry(key, language, 1):
            wordCount += 1

    logging.info('Finished creating dictionary ...')
    logging.info('Dictionary: {} words, {} entries, edit distance= {}'.format(wordCount, len(self.dictionary), self.editDistanceMax))

  def compareTo (self, a, b):
    if a > b:
      return 1
    if a < b:
      return -1
    return 0

  def Lookup (self, input, language, editDistanceMax):
    if (len(input) - editDistanceMax > self.maxlength):
      return list()

    candidates = list()
    hashset1 = set()

    suggestions = list()
    hashset2 = set()

    candidates.append(input)


    # End while
    def sort ():
      if (self.verbose < 2):
        sorted(suggestions, key = lambda xy: -self.compareTo(xy[0].count, xy[1].count))
      else:
        sorted(suggestions, key = lambda xy: 2 * self.compareTo(xy[0].distance, xy[1].distance) - self.compareTo(xy[0].count, xy[1].count))

    while len(candidates) > 0:
      candidate = candidates[0]
      del candidates[0]

      if (len(suggestions) > 0 and
          (len(input) - len(candidates) > suggestions[0].distance)
        ):
        sort()
        break

      valueo = self.dictionary.get(language + candidate)

      if valueo is not None:
        value = dictionaryItem()
        if valueo >= 0:
          value.suggestions.append(valueo)
        else:
          value = self.itemlist[-valueo - 1]

        if value.count > 0 and candidate not in hashset2:
          hashset2.add(candidate)
          distance = len(input) - len(candidate)

          if (self.verbose == 2 or
              len(suggestions) == 0 or
              distance <= suggestions[0].distance
            ):
            if (self.verbose < 2 and
                len(suggestions) > 0 and
                suggestions[0].distance > distance
              ):
              suggestions =[]

              si = suggestItem()
              si.term = candidate
              si.count = value.count
              si.distance = distance

              suggestions.append(si)

              if ((self.verbose < 2) and
                  (len(input) - len(candidate) == 0)
                  ):
                sort()
                break
        # End if

        for suggestionint in value.suggestions:
          suggestion = self.wordlist[suggestionint]

          if suggestion not in hashset2:
            hashset2.add(suggestion)
            distance = 0
            if suggestion != input:
              if (len(suggestion) == len(candidate)):
                distance = len(input) - len(candidate)
              elif (len(input) == len(candidate)):
                distance = len(suggestion) - len(candidate)
              else:
                ii = 0
                jj = 0
                while (
                    (ii < len(suggestion)) and
                    (ii < len(input)) and
                    (suggestion[ii] == input[ii])
                  ):
                  ii += 1
                while (
                  (jj < len(suggestion) - ii) and
                  (jj < len(input) - ii) and
                  (suggestion[len(suggestion) - jj - 1] == input[len(input) - jj - 1])
                  ):
                  jj += 1

                if ((ii > 0) or (jj > 0)):
                  distance = self.DamerauLevenshteinDistance(
                    suggestion[ii:len(suggestion) - jj],
                    input[ii:len(input) - jj]
                  )
                else:
                  distance = self.DamerauLevenshteinDistance(suggestion, input)

            # End if
            if ((self.verbose < 2) and (len(suggestions) > 0) and (distance > suggestions[0].distance)):continue

            if distance <= editDistanceMax:
              value2 = self.dictionary.get(language + suggestion)
              if value2 is not None:
                si = suggestItem()
                si.term = suggestion
                si.count = self.itemlist[-value2 - 1].count
                si.distance = distance

                if ((self.verbose < 2) and
                    (len(suggestions) > 0) and (suggestions[0].distance > distance)
                  ):
                  suggestions = []
                suggestions.append(si)


      # end for each
      else:
        if len(input) - len(candidate) < self.editDistanceMax:
          if ((self.verbose < 2) and
              (len(suggestions) > 0) and
                (len(input) - len(candidate) >= suggestions[0].distance)):
            continue

          for i in range(0, len(candidate)):
            delete = candidate[:i] + candidate[i + 1:]
            if delete not in hashset1:
              hashset1.add(delete)
              candidates.append(delete)

    if ((self.verbose == 0) and
        (len(suggestions) > 1)):
      return suggestions[:1]
    else:
      return suggestions


  def LookupCompound (self, input, language, editDistanceMax):
    termList1 = self.parseWords(input)
    suggestions = list()
    suggestionParts = list()

    lastCombi = False

    for i in range(0, len(termList1)):
      suggestionsPreviousTerm = list()
      for k in range(0, len(suggestions)):
        suggestionsPreviousTerm.append(suggestions[k].ShallowCopy())
      suggestions = self.Lookup(termList1[i], language, editDistanceMax)

      if ((i > 0) and not lastCombi):
        suggestionsCombi = self.Lookup(termList1[i - 1] + termList1[i], language, editDistanceMax)
        if len(suggestionsCombi) > 0:
          best1 = suggestionParts[len(suggestionParts) - 1]
          best2 = suggestItem()
          if len(suggestions) > 0:
            best2 = suggestions[0]
          else:
            best2.term = termList1[i]
            best2.distance = editDistanceMax + 1
            best2.count = 0

          if suggestionsCombi[0].distance + 1 < self.DamerauLevenshteinDistance(termList1[i - 1] + " " + termList1[i], best1.term + " " + best2.term):
            suggestionsCombi[0].distance += 1
            suggestionParts[len(suggestionParts) - 1] = suggestionsCombi[0]
            lastCombi = True

            continue

      # Endif
      lastCombi = False

      if ((len(suggestions) > 0) and ((suggestions[0].distance==0)  or (len(termList1[i]) == 1))):
        suggestionParts.append(suggestions[0]);
      else:
        suggestionsSplit = list()

        if (len(suggestions) > 0):
          suggestionsSplit.append(suggestions[0]);

        if (len(termList1[i]) > 1):
          for j in range(0, len(termList1[i])):
            part1 = termList1[i][0:j]
            part2 = termList1[i][j:]
            suggestionSplit = suggestItem()

            suggestions1 = self.Lookup(part1, language, editDistanceMax)

            if (len(suggestions1) > 0):
              if ((len(suggestions) > 0) and (suggestions[0].term == suggestions1[0].term)):
                break
              suggestions2 = self.Lookup(part2, language, editDistanceMax)

              if (len(suggestions2) > 0):
                if ((len(suggestions) > 0) and (suggestions[0].term == suggestions2[0].term)):
                  break

                suggestionSplit.term = suggestions1[0].term + " " + suggestions2[0].term;
                suggestionSplit.distance = self.DamerauLevenshteinDistance(termList1[i], suggestions1[0].term + " " + suggestions2[0].term);
                suggestionSplit.count = min(suggestions1[0].count, suggestions2[0].count)
                suggestionsSplit.append(suggestionSplit)

                # early termination of split
                if (suggestionSplit.distance == 1):
                 break

          # End for
          if (len(suggestionsSplit) > 0):
            sorted(suggestionsSplit, key = lambda xy: 2 * self.compareTo(xy[0].distance, xy[1].distance) - self.compareTo(xy[0].count, xy[1].count))
            suggestionParts.append(suggestionsSplit[0])

          else:
            si = suggestItem()
            si.term = termList1[i]
            si.count = 0
            si.distance = editDistanceMax + 1
            suggestionParts.append(si)
        # end if
        else:
          si = suggestItem()
          si.term = termList1[i]
          si.count = 0
          si.distance = editDistanceMax + 1
          suggestionParts.append(si)

    suggestion = suggestItem()
    suggestion.count = sys.maxsize
    s = ""
    for si in suggestionParts:
      s += si.term + " "
      suggestion.count = min(suggestion.count, si.count)
    suggestion.term = s.strip()
    suggestion.distance = self.DamerauLevenshteinDistance(suggestion.term, input)

    suggestionsLine = list()
    suggestionsLine.append(suggestion)

    return suggestionsLine

  def Correct (self, input, language):
    suggestions = None
    if self.enableCompoundCheck:
      suggestions = self.LookupCompound(input, language, self.editDistanceMax)
    else:
      suggestions = self.Lookup(input, language, self.editDistanceMax)
    for suggestion in suggestions:
      logging.info('suggested term: ' + suggestion.term)

  # Damerau–Levenshtein distance algorithm and code
  # from http://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance (as retrieved in June 2012)
  def DamerauLevenshteinDistance (self, seq1, seq2):
    oneago = None
    thisrow = range(1, len(seq2) + 1) #[0]
    for x in range(0, len(seq1)):
      # Python lists wrap around for negative indices, so put the
      # leftmost column at the *end* of the list. This matches with
      # the zero-indexed strings and saves extra calculation.
      twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]
      for y in range(0, len(seq2)):
          delcost = oneago[y] + 1
          addcost = thisrow[y - 1] + 1
          subcost = oneago[y - 1] + (seq1[x] != seq2[y])
          thisrow[y] = min(delcost, addcost, subcost)
          # This block deals with transpositions
          if (x > 0 and y > 0 and seq1[x] == seq2[y - 1]
              and seq1[x-1] == seq2[y] and seq1[x] != seq2[y]):
              thisrow[y] = min(thisrow[y], twoago[y - 2] + 1)
    return thisrow[len(seq2) - 1]

if __name__ == '__main__':
  s = SymSpell()
  # print (s.dictionary)
  # s.Correct('pleas', '')
  s.Correct('lawz', '')
