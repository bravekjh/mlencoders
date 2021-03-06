# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import unicode_literals

import unittest

import numpy as np
import pandas as pd
from genty import genty
from genty import genty_dataset
from nose.tools import eq_
from nose.tools import ok_
from numpy.testing import assert_array_almost_equal
from numpy.testing import assert_array_equal
from numpy.testing import assert_raises

from mlencoders.target_encoder import TargetEncoder


@genty
class TargetEncoderTest(unittest.TestCase):

    @genty_dataset(
        default_params=({}, None, 'impute', 1, 1),
        some_params=({'cols': ['a'], 'handle_unseen': 'error', 'smoothing': 10}, ['a'], 'error', 1, 10),
        wrong_input=({'min_samples': 0}, None, 'impute', 1, 1),
    )
    def test_init(self, kwargs, cols, handle_unseen, min_samples, smoothing):
        enc = TargetEncoder(**kwargs)
        eq_(enc.cols, cols)
        eq_(enc.handle_unseen, handle_unseen)
        eq_(enc.min_samples, min_samples)
        eq_(enc.smoothing, smoothing)
        eq_(enc._imputed, None)
        eq_(enc._mapping, {})

    @genty_dataset(
        typo=('ignores',),
    )
    def test_init_wrong_input(self, handle_unseen):
        assert_raises(ValueError, TargetEncoder, None, handle_unseen)

    def test_transform_before_fit(self):
        enc = TargetEncoder()
        assert_raises(ValueError, enc.transform, 1)

    @genty_dataset(
        some_input=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], 1, 1, [0.933, 0.933, 0.567, 0.567], 0.75, ['a', 'b']),
        min_sample_1=(['a', 'a', 'b', 'c'], [1, 1, 0, 1], 1, 1, [0.933, 0.933, 0.750, 0.750], 0.75, ['a', 'b', 'c']),
        min_sample_2=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], 2, 1, [0.750, 0.750, 0.750, 0.750], 0.75, ['a', 'b']),
        smoothing=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], 1, 2, [0.906, 0.906, 0.594, 0.594], 0.75, ['a', 'b']),
    )
    def test_encode_col(self, X, y, min_samples, smoothing, expected, imputed, columns):
        enc = TargetEncoder(cols=['cat'], min_samples=min_samples, smoothing=smoothing)
        result = enc.fit_transform(pd.DataFrame(X, columns=['cat']), pd.Series(y))
        assert_array_almost_equal(result, pd.DataFrame(expected), decimal=3)
        eq_(enc._imputed, imputed)
        ok_('cat' in enc._mapping)
        ok_(isinstance(enc._mapping['cat'], pd.DataFrame))
        assert_array_equal(enc._mapping['cat'].index, columns)
        assert_array_equal(enc._mapping['cat'].columns, ['mean', 'count', 'value'])

    @genty_dataset(
        some_input=(['a', 'a', np.nan, 'b'], [1, 1, 0, 1], [0.933, 0.933, 0.750, 0.750], ['a', 'b']),
    )
    def test_encode_nans(self, X, y, expected, columns):
        enc = TargetEncoder(cols=['cat'])
        result = enc.fit_transform(pd.DataFrame(X, columns=['cat']), pd.Series(y))
        assert_array_almost_equal(result, pd.DataFrame(expected), decimal=3)
        ok_('cat' in enc._mapping)
        ok_(isinstance(enc._mapping['cat'], pd.DataFrame))
        eq_(enc._mapping['cat'].index[0], -99999)
        assert_array_equal(enc._mapping['cat'].index[1:], columns)
        assert_array_equal(enc._mapping['cat'].columns, ['mean', 'count', 'value'])

    @genty_dataset(
        impute=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], ['foo', 'a', 'b'], 'impute', [0.750, 0.933, 0.567]),
        impute_all=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], ['foo', 'foo', 'foo'], 'impute', [0.750, 0.750, 0.750]),
        ignore=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], ['foo', 'a', 'b'], 'ignore', [np.nan, 0.933, 0.567]),
        ignore_all=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], ['foo', 'foo', 'foo'], 'ignore', [np.nan, np.nan, np.nan]),
    )
    def test_transform_unseen(self, X, y, Z, handle_unseen, expected):
        enc = TargetEncoder(cols=['cat'], handle_unseen=handle_unseen)
        X = pd.DataFrame(X, columns=['cat'])
        enc.fit(X, pd.Series(y))
        result = enc.transform(pd.DataFrame(Z, columns=['cat']))
        assert_array_almost_equal(result, pd.DataFrame(expected), decimal=3)

    @genty_dataset(
        impute=(['a', 'a', 'b', 'b'], [1, 1, 0, 1], [0.750, 0.933, 0.567, 0.567]),
    )
    def test_transform_error(self, X, y, expected):
        enc = TargetEncoder(cols=['cat'], handle_unseen='error')
        X = pd.DataFrame(X, columns=['cat'])
        enc.fit(X, pd.Series(y))
        X.iloc[0, 0] = 'foo'
        assert_raises(ValueError, enc.transform, X)

    @genty_dataset(
        some_input=([['a', 'foo'], ['a', 'bar'], ['b', 'foo']], [1, 0, 1], [[0.54, 0.91], [0.54, 0.67], [0.67, 0.91]]),
    )
    def test_encode_multiple_cols(self, X, y, expected):
        enc = TargetEncoder(cols=['cat1', 'cat2'])
        result = enc.fit_transform(pd.DataFrame(X, columns=['cat1', 'cat2']), pd.Series(y))
        assert_array_almost_equal(result, pd.DataFrame(expected), decimal=2)
        ok_('cat1' in enc._mapping)
        ok_('cat2' in enc._mapping)
        ok_(isinstance(enc._mapping['cat1'], pd.DataFrame))
        ok_(isinstance(enc._mapping['cat2'], pd.DataFrame))
        assert_array_equal(enc._mapping['cat1'].index, ['a', 'b'])
        assert_array_equal(enc._mapping['cat2'].index, ['bar', 'foo'])
        assert_array_equal(enc._mapping['cat1'].columns, ['mean', 'count', 'value'])
        assert_array_equal(enc._mapping['cat2'].columns, ['mean', 'count', 'value'])

    @genty_dataset(
        some_input=([['a', 'foo'], ['a', 'bar'], ['b', 'foo']], [1, 0, 1], [[0.54, 0.91], [0.54, 0.67], [0.67, 0.91]]),
    )
    def test_encode_all(self, X, y, expected):
        # all columns are encoded if no cols arg passed
        enc = TargetEncoder()
        result = enc.fit_transform(pd.DataFrame(X, columns=['cat1', 'cat2']), pd.Series(y))
        assert_array_almost_equal(result, pd.DataFrame(expected), decimal=2)
        assert_array_equal(enc.cols, ['cat1', 'cat2'])
        ok_('cat1' in enc._mapping)
        ok_('cat2' in enc._mapping)
        ok_(isinstance(enc._mapping['cat1'], pd.DataFrame))
        ok_(isinstance(enc._mapping['cat2'], pd.DataFrame))
        assert_array_equal(enc._mapping['cat1'].index, ['a', 'b'])
        assert_array_equal(enc._mapping['cat2'].index, ['bar', 'foo'])
        assert_array_equal(enc._mapping['cat1'].columns, ['mean', 'count', 'value'])
        assert_array_equal(enc._mapping['cat2'].columns, ['mean', 'count', 'value'])
