#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from unittest import TestCase, skip

from ..tools import parsedate, geopoint, distance, ngrams, flatten, tokenize, jw, levenshtein, levenshtein_norm
from ..tools import match_lv1, match_jw
from datetime import datetime


class ToolsTestCase(TestCase):

    def test_parsedate(self):
        """ it should parse a serialized (string) date into a datetime object according to a specific format"""
        serialized = "19890226"
        parsed = parsedate(serialized, format="%Y%m%d")
        expected = datetime(1989, 2, 26)
        self.assertEqual(parsed, expected)

    def test_geopoint(self):
        gp_str = "POINT(48.864716 2.349014)"
        gp = geopoint(gp_str)
        expected = (2.349014, 48.864716)
        self.assertEqual(gp, expected)

    def test_distance(self):
        """ it should calculate the distance in km between two geo points """
        A = "POINT(48.864716 2.349014)"
        B = "POINT(45.239403 4.667349)"
        dist = distance(A, B)
        expected_dist = 477.4
        self.assertEqual(dist, expected_dist)

    def test_ngrams(self):
        """ it should calculates the n-gram (https://en.wikipedia.org/wiki/N-gram) of a string """
        ngrams_n3 = ngrams("matchid", n=[3])
        expected_n3 = ['mat', 'atc', 'tch', 'chi', 'hid']
        self.assertEqual(ngrams_n3, expected_n3)
        ngrams_n2 = ngrams("matchid", n=[2])
        expected_n2 = ['ma', 'at', 'tc', 'ch', 'hi', 'id']
        self.assertEqual(ngrams_n2, expected_n2)
        ngrams_n23 = ngrams("matchid", n=[2, 3])
        expected_n23 = ['ma', 'at', 'tc', 'ch', 'hi', 'id', 'mat', 'atc', 'tch', 'chi', 'hid']
        self.assertEqual(ngrams_n23, expected_n23)

    def test_flatten(self):
        """ it should flatten a list of list """
        list_of_list = [[1, 2], [3, 4]]
        flattened = flatten(list_of_list)
        expected = [1, 2, 3, 4]
        self.assertEqual(flattened, expected)

    def test_tokenize(self):
        """ it should create a list of tokens from a phrase or a list of phrases """
        phrase = "This is Ground Control to Major Tom"
        tokenized = tokenize(phrase)
        expected = ['This', 'is', 'Ground', 'Control', 'to', 'Major', 'Tom']
        self.assertEqual(tokenized, expected)
        list_of_phrases = [
            "This is Ground Control to Major Tom.",
            "You've really made the grade",
            "And the papers want to know whose shirts you wear"
        ]
        tokenized = tokenize(list_of_phrases)
        expected = ['This', 'is', 'Ground', 'Control', 'to', 'Major', 'Tom.', "You've", 'really', 'made', 'the',
                    'grade', 'And', 'the', 'papers', 'want', 'to', 'know', 'whose', 'shirts', 'you', 'wear']
        self.assertEqual(tokenized, expected)

    def test_jw(self):
        """ it should calculate the Jaro-Winkler similarity between two strings """
        similarity = jw("matchID", "matchID")
        self.assertEqual(similarity, 1.0)
        similarity = jw("totally", "different")
        self.assertEqual(similarity, 0.0)
        similarity = jw("matchID", "macthDI")
        self.assertEqual(similarity, 0.92)

    def test_levenshtein(self):
        """ it should calculate the Levenshtein distance between two strings """
        d = levenshtein("matchID", "matchID")
        self.assertEqual(d, 0.0)
        # one character to replace d == 1
        d = levenshtein("matchID", "MatchID")
        self.assertEqual(d, 1.0)
        # two characters to replace d == 2
        d = levenshtein("matchID", "matchDI")
        self.assertEqual(d, 2.0)

    def test_levenshtein_norm(self):
        """ it should calculate the levenshtein similarity between two strings """
        d = levenshtein_norm("matchID", "matchID")
        self.assertEqual(d, 1.0)
        d = levenshtein_norm("totally", "different")
        self.assertEqual(d, 0.0)
        d = levenshtein_norm("matchID", "matchDI")
        self.assertEqual(d, 0.75)

    @skip("Fail because global name 'compare' is not defined")
    def test_match_lv1(self):
        """ it should return the best match according to Levensthein distance, or None if distance is too large """
        to_be_matched = "Jack Bauer"
        match_from = ["Jack Kerouac", "Jack Boher", "Jacques Bauer"]
        match = match_lv1(to_be_matched, match_from)
        expected_match = None
        self.assertEqual(match, expected_match)
        match_from = ["Jack Kerouac", "Jack Boher", "Jack Bauere"]
        match = match_lv1(to_be_matched, match_from)
        expected_match = "Jack Bauere"
        self.assertEqual(match, expected_match)

    def test_match_jw(self):
        """ it should return the best match according to Jaro-Winkler distance, or None if distance is too large """
        to_be_matched = "Jack Bauer"
        match_from = ["Jack Kerouac", "Jack Boher", "Jacques Bauer"]
        match = match_jw(to_be_matched, match_from)
        expected_match = None
        self.assertEqual(match, expected_match)
        match_from = ["Jack Kerouac", "Jack Boher", "Jack Bauere"]
        match = match_jw(to_be_matched, match_from)
        expected_match = "Jack Bauere"
        self.assertEqual(match, expected_match)


