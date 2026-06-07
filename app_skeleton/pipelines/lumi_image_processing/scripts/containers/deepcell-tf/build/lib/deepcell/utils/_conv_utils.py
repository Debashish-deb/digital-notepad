# Copyright 2016-2024 The Van Valen Lab at the California Institute of
# Technology (Caltech), with support from the Paul Allen Family Foundation,
# Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
# All rights reserved.
#
# Licensed under a modified Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.github.com/vanvalenlab/deepcell-tf/LICENSE
#
# The Work provided may be used for non-commercial academic purposes only.
# For any other use of the Work, including commercial use, please contact:
# vanvalenlab@gmail.com
#
# Neither the name of Caltech nor the names of its contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Compatibility shim for keras.utils.conv_utils.

keras.utils.conv_utils is an internal module that was removed from the public
API in Keras 3 and is not exposed by tf_keras.utils. This module re-implements
the subset of functions used by deepcell-tf so the codebase remains runnable
under TensorFlow 2.18 + tf-keras (legacy Keras 2).
"""

import tensorflow as tf


def normalize_data_format(value):
    """Normalize the data format string.

    Args:
        value (str or None): 'channels_first', 'channels_last', or None.
            If None, falls back to the Keras global image data format.

    Returns:
        str: Normalized data format string.

    Raises:
        ValueError: If value is not a valid data format.
    """
    if value is None:
        value = tf.keras.backend.image_data_format()
    data_formats = {'channels_first', 'channels_last'}
    if value not in data_formats:
        raise ValueError(
            f'The `data_format` argument must be one of '
            f'"channels_first", "channels_last". Received: "{value}"'
        )
    return value


def normalize_tuple(value, n, name, allow_zero=False):
    """Normalize an int or tuple to a tuple of length n.

    Args:
        value (int or tuple): The value to normalize.
        n (int): The expected length of the resulting tuple.
        name (str): The name of the argument (for error messages).
        allow_zero (bool): Whether zero values are permitted.

    Returns:
        tuple: Tuple of n ints.

    Raises:
        ValueError: On invalid input.
    """
    error_msg = (
        f'The `{name}` argument must be a tuple of {n} integers. '
        f'Received: {name}={value}.'
    )
    if isinstance(value, int):
        value_tuple = (value,) * n
    else:
        try:
            value_tuple = tuple(value)
        except TypeError:
            raise ValueError(error_msg)
        if len(value_tuple) != n:
            raise ValueError(error_msg)
        for single_value in value_tuple:
            if not isinstance(single_value, int):
                raise ValueError(
                    f'The `{name}` argument must be a tuple of {n} integers. '
                    f'Received: {name}={value} including element '
                    f'{single_value} of type {type(single_value)}'
                )
    if allow_zero:
        unqualified_values = {v for v in value_tuple if v < 0}
        req_msg = '>= 0'
    else:
        unqualified_values = {v for v in value_tuple if v <= 0}
        req_msg = '> 0'
    if unqualified_values:
        raise ValueError(
            f'The `{name}` argument must be a tuple of {n} integers '
            f'{req_msg}. Received: {name}={value_tuple}.'
        )
    return value_tuple


def normalize_padding(value):
    """Normalize a padding string.

    Args:
        value (str): 'valid', 'same', or 'causal'.

    Returns:
        str: Lowercased padding string.

    Raises:
        ValueError: If value is not a valid padding type.
    """
    if isinstance(value, (list, tuple)):
        return value
    padding = value.lower()
    if padding not in {'valid', 'same', 'causal'}:
        raise ValueError(
            f'The `padding` argument must be one of '
            f'"valid", "same", "causal". Received: "{padding}"'
        )
    return padding


def conv_output_length(input_length, filter_size, padding, stride, dilation=1):
    """Compute the output length of a convolution given the input length.

    Args:
        input_length (int or None): Length of the input.
        filter_size (int): Size of the convolution filter.
        padding (str): 'same', 'valid', 'full', or 'causal'.
        stride (int): Stride of the convolution.
        dilation (int): Dilation rate for the convolution.

    Returns:
        int or None: Output length, or None if input_length is None.
    """
    if input_length is None:
        return None
    dilated_filter_size = filter_size + (filter_size - 1) * (dilation - 1)
    if padding in ('same', 'causal'):
        output_length = input_length
    elif padding == 'valid':
        output_length = input_length - dilated_filter_size + 1
    elif padding == 'full':
        output_length = input_length + dilated_filter_size - 1
    else:
        raise ValueError(
            f'Invalid padding: "{padding}". '
            f'Expected one of "same", "valid", "full", "causal".'
        )
    return (output_length + stride - 1) // stride
