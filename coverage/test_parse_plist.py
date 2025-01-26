#!/bin/env python

import io
from random import randrange
import unittest

import parse_plist

def parse(params):
    return parse_plist.get_plist(params)

class Test(unittest.TestCase):

    def test_1(self):
        self.assertEqual('', parse(''))

    def test_2(self):
        self.assertEqual('int', parse('int x'))

    def test_3(self):
        self.assertEqual('int[]', parse('int[] x'))

    def test_4(self):
        self.assertEqual('List<String>', parse('List<String> l'))

    def test_5(self):
        self.assertEqual('int[],List<String>', parse('int[] x, List<String> l'))

    def test_6(self):
        self.assertEqual('List<String>,int[]', parse('List<String> l, int[] x'))

    def test_7(self):
        self.assertEqual('List<String>', parse('List&lt;String&gt; l'))

    # Trailing simple parameter(s) behind array split.
    def test_8(self):
        with self.subTest():
            self.assertEqual('T[],T', parse('T[] x, T x'))
        with self.subTest():
            self.assertEqual('T[],T,T', parse('T[] x, T x, T x'))
        with self.subTest():
            self.assertEqual('T[],T,T[],T', parse('T[] x, T x, T[] x, T x'))
        with self.subTest():
            self.assertEqual('T[],T<T>,T', parse('T[] x, T<T> x, T x'))

    # Trailing simple parameter(s) behind generic split.
    def test_9(self):
        with self.subTest():
            self.assertEqual('T<X>,T', parse('T<X> x, T x'))
        with self.subTest():
            self.assertEqual('T<X>,T,T', parse('T<X> x, T x, T x'))
        with self.subTest():
            self.assertEqual('T<X>,T,T<X>,T', parse('T<X> x, T x, T<X> x, T x'))

    def write_random_type(self, signature, parameter_list, limit, depth = 0):
        # Force simple type at 'limit' to limit recursion depth.
        if depth < limit:
            signature.write('T')
            parameter_list.write('T')
            if randrange(3) == 1: # 33% chance
                signature.write('<')
                parameter_list.write('<')
                first = True
                for i in range(randrange(limit - depth) + 1):
                    if not first:
                        signature.write(',')
                        parameter_list.write(',')
                    first = False
                    self.write_random_type(signature, parameter_list, limit, depth + 1)
                signature.write('>')
                parameter_list.write('>')
            brackets = '[]' * randrange(limit - depth)
            signature.write(brackets)
            parameter_list.write(brackets + (" x" if depth == 0 else ""))
        else:
            signature.write('T')
            parameter_list.write('T' + (" x" if depth == 0 else ""))

    def random_pair(self):
        with io.StringIO() as signature:
            with io.StringIO() as parameter_list:
                first = True
                limit = 3
                for i in range(randrange(3) + 1):
                    if not first:
                        signature.write(',')
                        parameter_list.write(', ')
                    first = False
                    self.write_random_type(signature, parameter_list, limit)
                return (signature.getvalue(), parameter_list.getvalue())

    @unittest.skip("Random tests. Random input to try to find unhandled cases.")
    def test_x(self):
        for i in range(1000):
            with self.subTest(i = i):
                p = self.random_pair()
                print("Parsing", p)
                self.assertEqual(p[0], parse(p[1]))

if __name__ == '__main__':
    unittest.main()

