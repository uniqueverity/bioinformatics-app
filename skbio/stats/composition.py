r"""Composition Statistics (:mod:`skbio.stats.composition`)
=======================================================

.. currentmodule:: skbio.stats.composition

This module provides functions for compositional data analysis.

Many 'omics datasets are inherently compositional - meaning that they
are best interpreted as proportions or percentages rather than
absolute counts.

Formally, :math:`x` is a composition if :math:`\sum_{i=0}^D x_{i} = c`
and :math:`x_{i} > 0`, :math:`1 \leq i \leq D` and :math:`c` is a real
valued constant and there are :math:`D` components for each
composition. In this module :math:`c=1`. Compositional data can be
analyzed using Aitchison geometry. [1]_

However, in this framework, standard real Euclidean operations such as
addition and multiplication no longer apply. Only operations such as
perturbation and power can be used to manipulate this data.

This module allows two styles of manipulation of compositional data.
Compositional data can be analyzed using perturbation and power
operations, which can be useful for simulation studies. The
alternative strategy is to transform compositional data into the real
space.  Right now, the centre log ratio transform (clr) and
the isometric log ratio transform (ilr) [2]_ can be used to accomplish
this. This transform can be useful for performing standard statistical
tools such as parametric hypothesis testing, regressions and more.

The major caveat of using this framework is dealing with zeros.  In
the Aitchison geometry, only compositions with nonzero components can
be considered. The multiplicative replacement technique [3]_ can be
used to substitute these zeros with small pseudocounts without
introducing major distortions to the data.

Functions
---------

.. autosummary::
   :toctree:

   closure
   multiplicative_replacement
   perturb
   perturb_inv
   power
   inner
   clr
   clr_inv
   ilr
   ilr_inv
   alr
   alr_inv
   centralize
   vlr
   pairwise_vlr
   tree_basis
   ancom
   sbp_basis
   dirmult_ttest


References
----------
.. [1] V. Pawlowsky-Glahn, J. J. Egozcue, R. Tolosana-Delgado (2015),
   Modeling and Analysis of Compositional Data, Wiley, Chichester, UK

.. [2] J. J. Egozcue.,  "Isometric Logratio Transformations for
   Compositional Data Analysis" Mathematical Geology, 35.3 (2003)

.. [3] J. A. Martin-Fernandez,  "Dealing With Zeros and Missing Values in
   Compositional Data Sets Using Nonparametric Imputation",
   Mathematical Geology, 35.3 (2003)


Examples
--------
>>> import numpy as np

Consider a very simple environment with only 3 species. The species
in the environment are equally distributed and their proportions are
equivalent:

>>> otus = np.array([1./3, 1./3., 1./3])

Suppose that an antibiotic kills off half of the population for the
first two species, but doesn't harm the third species. Then the
perturbation vector would be as follows

>>> antibiotic = np.array([1./2, 1./2, 1])

And the resulting perturbation would be

>>> perturb(otus, antibiotic)
array([ 0.25,  0.25,  0.5 ])


"""  # noqa: D205, D415

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# ----------------------------------------------------------------------------

import numpy as np
import pandas as pd
import scipy.stats
import skbio.util
from skbio.util._decorator import experimental
from skbio.stats.distance import DistanceMatrix
from skbio.util._misc import get_rng
from scipy.sparse import coo_matrix
from scipy.stats import t


@experimental(as_of="0.4.0")
def closure(mat):
    """Perform closure to ensure that all elements add up to 1.

    Parameters
    ----------
    mat : array_like
       a matrix of proportions where
       rows = compositions
       columns = components

    Returns
    -------
    array_like, np.float64
       A matrix of proportions where all of the values
       are nonzero and each composition (row) adds up to 1

    Raises
    ------
    ValueError
       Raises an error if any values are negative.
    ValueError
       Raises an error if the matrix has more than 2 dimension.
    ValueError
       Raises an error if there is a row that has all zeros.

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import closure
    >>> X = np.array([[2, 2, 6], [4, 4, 2]])
    >>> closure(X)
    array([[ 0.2,  0.2,  0.6],
           [ 0.4,  0.4,  0.2]])

    """
    mat = np.atleast_2d(mat)
    if np.any(mat < 0):
        raise ValueError("Cannot have negative proportions")
    if mat.ndim > 2:
        raise ValueError("Input matrix can only have two dimensions or less")
    if np.all(mat == 0, axis=1).sum() > 0:
        raise ValueError("Input matrix cannot have rows with all zeros")
    mat = mat / mat.sum(axis=1, keepdims=True)
    return mat.squeeze()


@experimental(as_of="0.4.0")
def multiplicative_replacement(mat, delta=None):
    r"""Replace all zeros with small non-zero values.

    It uses the multiplicative replacement strategy [1]_ ,
    replacing zeros with a small positive :math:`\delta`
    and ensuring that the compositions still add up to 1.


    Parameters
    ----------
    mat: array_like
       a matrix of proportions where
       rows = compositions and
       columns = components
    delta: float, optional
       a small number to be used to replace zeros
       If delta is not specified, then the default delta is
       :math:`\delta = \frac{1}{N^2}` where :math:`N`
       is the number of components

    Returns
    -------
    numpy.ndarray, np.float64
       A matrix of proportions where all of the values
       are nonzero and each composition (row) adds up to 1

    Raises
    ------
    ValueError
       Raises an error if negative proportions are created due to a large
       `delta`.

    Notes
    -----
    This method will result in negative proportions if a large delta is chosen.

    References
    ----------
    .. [1] J. A. Martin-Fernandez. "Dealing With Zeros and Missing Values in
           Compositional Data Sets Using Nonparametric Imputation"


    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import multiplicative_replacement
    >>> X = np.array([[.2,.4,.4, 0],[0,.5,.5,0]])
    >>> multiplicative_replacement(X)
    array([[ 0.1875,  0.375 ,  0.375 ,  0.0625],
           [ 0.0625,  0.4375,  0.4375,  0.0625]])

    """
    mat = closure(mat)
    z_mat = mat == 0

    num_feats = mat.shape[-1]
    tot = z_mat.sum(axis=-1, keepdims=True)

    if delta is None:
        delta = (1.0 / num_feats) ** 2

    zcnts = 1 - tot * delta
    if np.any(zcnts) < 0:
        raise ValueError(
            "The multiplicative replacement created negative "
            "proportions. Consider using a smaller `delta`."
        )
    mat = np.where(z_mat, delta, zcnts * mat)
    return mat.squeeze()


@experimental(as_of="0.4.0")
def perturb(x, y):
    r"""Perform the perturbation operation.

    This operation is defined as

    .. math::
        x \oplus y = C[x_1 y_1, \ldots, x_D y_D]

    :math:`C[x]` is the closure operation defined as

    .. math::
        C[x] = \left[\frac{x_1}{\sum_{i=1}^{D} x_i},\ldots,
                     \frac{x_D}{\sum_{i=1}^{D} x_i} \right]

    for some :math:`D` dimensional real vector :math:`x` and
    :math:`D` is the number of components for every composition.

    Parameters
    ----------
    x : array_like, float
        a matrix of proportions where
        rows = compositions and
        columns = components
    y : array_like, float
        a matrix of proportions where
        rows = compositions and
        columns = components

    Returns
    -------
    numpy.ndarray, np.float64
       A matrix of proportions where all of the values
       are nonzero and each composition (row) adds up to 1

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import perturb
    >>> x = np.array([.1,.3,.4, .2])
    >>> y = np.array([1./6,1./6,1./3,1./3])
    >>> perturb(x,y)
    array([ 0.0625,  0.1875,  0.5   ,  0.25  ])

    """
    x, y = closure(x), closure(y)
    return closure(x * y)


@experimental(as_of="0.4.0")
def perturb_inv(x, y):
    r"""Perform the inverse perturbation operation.

    This operation is defined as

    .. math::
        x \ominus y = C[x_1 y_1^{-1}, \ldots, x_D y_D^{-1}]

    :math:`C[x]` is the closure operation defined as

    .. math::
        C[x] = \left[\frac{x_1}{\sum_{i=1}^{D} x_i},\ldots,
                     \frac{x_D}{\sum_{i=1}^{D} x_i} \right]


    for some :math:`D` dimensional real vector :math:`x` and
    :math:`D` is the number of components for every composition.

    Parameters
    ----------
    x : array_like
        a matrix of proportions where
        rows = compositions and
        columns = components
    y : array_like
        a matrix of proportions where
        rows = compositions and
        columns = components

    Returns
    -------
    numpy.ndarray, np.float64
       A matrix of proportions where all of the values
       are nonzero and each composition (row) adds up to 1

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import perturb_inv
    >>> x = np.array([.1,.3,.4, .2])
    >>> y = np.array([1./6,1./6,1./3,1./3])
    >>> perturb_inv(x,y)
    array([ 0.14285714,  0.42857143,  0.28571429,  0.14285714])

    """
    x, y = closure(x), closure(y)
    return closure(x / y)


@experimental(as_of="0.4.0")
def power(x, a):
    r"""Perform the power operation.

    This operation is defined as follows

    .. math::
        `x \odot a = C[x_1^a, \ldots, x_D^a]

    :math:`C[x]` is the closure operation defined as

    .. math::
        C[x] = \left[\frac{x_1}{\sum_{i=1}^{D} x_i},\ldots,
                     \frac{x_D}{\sum_{i=1}^{D} x_i} \right]

    for some :math:`D` dimensional real vector :math:`x` and
    :math:`D` is the number of components for every composition.

    Parameters
    ----------
    x : array_like, float
        a matrix of proportions where
        rows = compositions and
        columns = components
    a : float
        a scalar float

    Returns
    -------
    numpy.ndarray, np.float64
       A matrix of proportions where all of the values
       are nonzero and each composition (row) adds up to 1

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import power
    >>> x = np.array([.1,.3,.4, .2])
    >>> power(x, .1)
    array([ 0.23059566,  0.25737316,  0.26488486,  0.24714631])

    """
    x = closure(x)
    return closure(x**a).squeeze()


@experimental(as_of="0.4.0")
def inner(x, y):
    r"""Calculate the Aitchson inner product.

    This inner product is defined as follows

    .. math::
        \langle x, y \rangle_a =
        \frac{1}{2D} \sum\limits_{i=1}^{D} \sum\limits_{j=1}^{D}
        \ln\left(\frac{x_i}{x_j}\right) \ln\left(\frac{y_i}{y_j}\right)

    Parameters
    ----------
    x : array_like
        a matrix of proportions where
        rows = compositions and
        columns = components
    y : array_like
        a matrix of proportions where
        rows = compositions and
        columns = components

    Returns
    -------
    numpy.ndarray
         inner product result

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import inner
    >>> x = np.array([.1, .3, .4, .2])
    >>> y = np.array([.2, .4, .2, .2])
    >>> inner(x, y)  # doctest: +ELLIPSIS
    0.2107852473...

    """
    x = closure(x)
    y = closure(y)
    a, b = clr(x), clr(y)
    return a.dot(b.T)


@experimental(as_of="0.4.0")
def clr(mat):
    r"""Perform centre log ratio transformation.

    This function transforms compositions from Aitchison geometry to
    the real space. The :math:`clr` transform is both an isometry and an
    isomorphism defined on the following spaces

    :math:`clr: S^D \rightarrow U`

    where :math:`U=
    \{x :\sum\limits_{i=1}^D x = 0 \; \forall x \in \mathbb{R}^D\}`

    It is defined for a composition :math:`x` as follows:

    .. math::
        clr(x) = \ln\left[\frac{x_1}{g_m(x)}, \ldots, \frac{x_D}{g_m(x)}\right]

    where :math:`g_m(x) = (\prod\limits_{i=1}^{D} x_i)^{1/D}` is the geometric
    mean of :math:`x`.

    Parameters
    ----------
    mat : array_like, float
       a matrix of proportions where
       rows = compositions and
       columns = components

    Returns
    -------
    numpy.ndarray
         clr transformed matrix

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import clr
    >>> x = np.array([.1, .3, .4, .2])
    >>> clr(x)
    array([-0.79451346,  0.30409883,  0.5917809 , -0.10136628])

    """
    mat = closure(mat)
    lmat = np.log(mat)
    gm = lmat.mean(axis=-1, keepdims=True)
    return (lmat - gm).squeeze()


@experimental(as_of="0.4.0")
def clr_inv(mat):
    r"""Perform inverse centre log ratio transformation.

    This function transforms compositions from the real space to
    Aitchison geometry. The :math:`clr^{-1}` transform is both an isometry,
    and an isomorphism defined on the following spaces

    :math:`clr^{-1}: U \rightarrow S^D`

    where :math:`U=
    \{x :\sum\limits_{i=1}^D x = 0 \; \forall x \in \mathbb{R}^D\}`

    This transformation is defined as follows

    .. math::
        clr^{-1}(x) = C[\exp( x_1, \ldots, x_D)]

    Parameters
    ----------
    mat : array_like, float
       a matrix of real values where
       rows = transformed compositions and
       columns = components

    Returns
    -------
    numpy.ndarray
         inverse clr transformed matrix

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import clr_inv
    >>> x = np.array([.1, .3, .4, .2])
    >>> clr_inv(x)
    array([ 0.21383822,  0.26118259,  0.28865141,  0.23632778])

    """
    # for numerical stability (aka softmax trick)
    mat = np.atleast_2d(mat)
    emat = np.exp(mat - mat.max(axis=-1, keepdims=True))
    return closure(emat)


@experimental(as_of="0.4.0")
def ilr(mat, basis=None, check=True):
    r"""Perform isometric log ratio transformation.

    This function transforms compositions from Aitchison simplex to
    the real space. The :math: ilr` transform is both an isometry,
    and an isomorphism defined on the following spaces

    :math:`ilr: S^D \rightarrow \mathbb{R}^{D-1}`

    The ilr transformation is defined as follows

    .. math::
        ilr(x) =
        [\langle x, e_1 \rangle_a, \ldots, \langle x, e_{D-1} \rangle_a]

    where :math:`[e_1,\ldots,e_{D-1}]` is an orthonormal basis in the simplex.

    If an orthornormal basis isn't specified, the J. J. Egozcue orthonormal
    basis derived from Gram-Schmidt orthogonalization will be used by
    default.

    Parameters
    ----------
    mat: numpy.ndarray
       a matrix of proportions where
       rows = compositions and
       columns = components

    basis: numpy.ndarray or scipy.sparse.matrix, optional
        orthonormal basis for Aitchison simplex
        defaults to J.J.Egozcue orthonormal basis.

    check: bool
        Specifies if the basis is orthonormal.

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import ilr
    >>> x = np.array([.1, .3, .4, .2])
    >>> ilr(x)
    array([-0.7768362 , -0.68339802,  0.11704769])

    Notes
    -----
    If the `basis` parameter is specified, it is expected to be a basis in the
    Aitchison simplex.  If there are `D-1` elements specified in `mat`, then
    the dimensions of the basis needs be `D-1 x D`, where rows represent
    basis vectors, and the columns represent proportions.

    """
    mat = closure(mat)
    if basis is None:
        d = mat.shape[-1]
        basis = _gram_schmidt_basis(d)  # dimension (d-1) x d
    else:
        if len(basis.shape) != 2:
            raise ValueError(
                "Basis needs to be a 2D matrix, "
                "not a %dD matrix." % (len(basis.shape))
            )
        if check:
            _check_orthogonality(basis)

    return clr(mat) @ basis.T


@experimental(as_of="0.4.0")
def ilr_inv(mat, basis=None, check=True):
    r"""Perform inverse isometric log ratio transform.

    This function transforms compositions from the real space to
    Aitchison geometry. The :math:`ilr^{-1}` transform is both an isometry,
    and an isomorphism defined on the following spaces

    :math:`ilr^{-1}: \mathbb{R}^{D-1} \rightarrow S^D`

    The inverse ilr transformation is defined as follows

    .. math::
        ilr^{-1}(x) = \bigoplus\limits_{i=1}^{D-1} x \odot e_i

    where :math:`[e_1,\ldots, e_{D-1}]` is an orthonormal basis in the simplex.

    If an orthonormal basis isn't specified, the J. J. Egozcue orthonormal
    basis derived from Gram-Schmidt orthogonalization will be used by
    default.


    Parameters
    ----------
    mat: numpy.ndarray, float
       a matrix of transformed proportions where
       rows = compositions and
       columns = components

    basis: numpy.ndarray, float, optional
        orthonormal basis for Aitchison simplex
        defaults to J.J.Egozcue orthonormal basis

    check: bool
        Specifies if the basis is orthonormal.


    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import ilr
    >>> x = np.array([.1, .3, .6,])
    >>> ilr_inv(x)
    array([ 0.34180297,  0.29672718,  0.22054469,  0.14092516])

    Notes
    -----
    If the `basis` parameter is specified, it is expected to be a basis in the
    Aitchison simplex.  If there are `D-1` elements specified in `mat`, then
    the dimensions of the basis needs be `D-1 x D`, where rows represent
    basis vectors, and the columns represent proportions.

    """
    mat = np.atleast_2d(mat)
    if basis is None:
        # dimension d-1 x d basis
        basis = _gram_schmidt_basis(mat.shape[-1] + 1)
    else:
        if len(basis.shape) != 2:
            raise ValueError(
                "Basis needs to be a 2D matrix, "
                "not a %dD matrix." % (len(basis.shape))
            )
        if check:
            _check_orthogonality(basis)
        # this is necessary, since the clr function
        # performs np.squeeze()
        basis = np.atleast_2d(basis)

    return clr_inv(mat @ basis)


@experimental(as_of="0.5.5")
def alr(mat, denominator_idx=0):
    r"""Perform additive log ratio transformation.

    This function transforms compositions from a D-part Aitchison simplex to
    a non-isometric real space of D-1 dimensions. The argument
    `denominator_col` defines the index of the column used as the common
    denominator. The :math: `alr` transformed data are amenable to multivariate
    analysis as long as statistics don't involve distances.

    :math:`alr: S^D \rightarrow \mathbb{R}^{D-1}`

    The alr transformation is defined as follows

    .. math::
        alr(x) = \left[ \ln \frac{x_1}{x_D}, \ldots,
        \ln \frac{x_{D-1}}{x_D} \right]

    where :math:`D` is the index of the part used as common denominator.

    Parameters
    ----------
    mat: numpy.ndarray
       a matrix of proportions where
       rows = compositions and
       columns = components

    denominator_idx: int
       the index of the column (2D-matrix) or position (vector) of
       `mat` which should be used as the reference composition. By default
       `denominator_idx=0` to specify the first column or position.

    Returns
    -------
    numpy.ndarray
         alr-transformed data projected in a non-isometric real space
         of D-1 dimensions for a D-parts composition

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import alr
    >>> x = np.array([.1, .3, .4, .2])
    >>> alr(x)
    array([ 1.09861229,  1.38629436,  0.69314718])

    """
    mat = closure(mat)
    if mat.ndim == 2:
        mat_t = mat.T
        numerator_idx = list(range(0, mat_t.shape[0]))
        del numerator_idx[denominator_idx]
        lr = np.log(mat_t[numerator_idx, :] / mat_t[denominator_idx, :]).T
    elif mat.ndim == 1:
        numerator_idx = list(range(0, mat.shape[0]))
        del numerator_idx[denominator_idx]
        lr = np.log(mat[numerator_idx] / mat[denominator_idx])
    else:
        raise ValueError("mat must be either 1D or 2D")
    return lr


@experimental(as_of="0.5.5")
def alr_inv(mat, denominator_idx=0):
    r"""Perform inverse additive log ratio transform.

    This function transforms compositions from the non-isometric real space of
    alrs to Aitchison geometry.

    :math:`alr^{-1}: \mathbb{R}^{D-1} \rightarrow S^D`

    The inverse alr transformation is defined as follows

    .. math::
         alr^{-1}(x) = C[exp([y_1, y_2, ..., y_{D-1}, 0])]

    where :math:`C[x]` is the closure operation defined as

    .. math::
        C[x] = \left[\frac{x_1}{\sum_{i=1}^{D} x_i},\ldots,
                     \frac{x_D}{\sum_{i=1}^{D} x_i} \right]

    for some :math:`D` dimensional real vector :math:`x` and
    :math:`D` is the number of components for every composition.

    Parameters
    ----------
    mat: numpy.ndarray
       a matrix of alr-transformed data
    denominator_idx: int
       the index of the column (2D-composition) or position (1D-composition) of
       the output where the common denominator should be placed. By default
       `denominator_idx=0` to specify the first column or position.

    Returns
    -------
    numpy.ndarray
         Inverse alr transformed matrix or vector where rows sum to 1.

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import alr, alr_inv
    >>> x = np.array([.1, .3, .4, .2])
    >>> alr_inv(alr(x))
    array([ 0.1,  0.3,  0.4,  0.2])

    """
    mat = np.array(mat)
    if mat.ndim == 2:
        mat_idx = np.insert(mat, denominator_idx, np.repeat(0, mat.shape[0]), axis=1)
        comp = np.zeros(mat_idx.shape)
        comp[:, denominator_idx] = 1 / (np.exp(mat).sum(axis=1) + 1)
        numerator_idx = list(range(0, comp.shape[1]))
        del numerator_idx[denominator_idx]
        for i in numerator_idx:
            comp[:, i] = comp[:, denominator_idx] * np.exp(mat_idx[:, i])
    elif mat.ndim == 1:
        mat_idx = np.insert(mat, denominator_idx, 0, axis=0)
        comp = np.zeros(mat_idx.shape)
        comp[denominator_idx] = 1 / (np.exp(mat).sum(axis=0) + 1)
        numerator_idx = list(range(0, comp.shape[0]))
        del numerator_idx[denominator_idx]
        for i in numerator_idx:
            comp[i] = comp[denominator_idx] * np.exp(mat_idx[i])
    else:
        raise ValueError("mat must be either 1D or 2D")
    return comp


@experimental(as_of="0.4.0")
def centralize(mat):
    r"""Center data around its geometric average.

    Parameters
    ----------
    mat : array_like, float
       a matrix of proportions where
       rows = compositions and
       columns = components

    Returns
    -------
    numpy.ndarray
         centered composition matrix

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import centralize
    >>> X = np.array([[.1,.3,.4, .2],[.2,.2,.2,.4]])
    >>> centralize(X)
    array([[ 0.17445763,  0.30216948,  0.34891526,  0.17445763],
           [ 0.32495488,  0.18761279,  0.16247744,  0.32495488]])

    """
    mat = closure(mat)
    cen = scipy.stats.gmean(mat, axis=0)
    return perturb_inv(mat, cen)


@experimental(as_of="0.5.7")
def _vlr(x: np.array, y: np.array, ddof: int):
    r"""Calculate variance log ratio.

    Parameters
    ----------
    x : array_like, float
        A 1-dimensional vector of proportions.
    y : array_like, float
        A 1-dimensional vector of proportions.
    ddof: int
        Degrees of freedom.

    Returns
    -------
    float
        Variance log ratio value.

    """
    # Log transformation
    x = np.log(x)
    y = np.log(y)

    # Variance log ratio
    return np.var(x - y, ddof=ddof)


@experimental(as_of="0.5.7")
def _robust_vlr(x: np.ndarray, y: np.ndarray, ddof: int):
    r"""Calculate variance log ratio while masking zeros.

    Parameters
    ----------
    x : array_like, float
        A 1-dimensional vector of proportions.
    y : array_like, float
        A 1-dimensional vector of proportions.
    ddof: int
        Degrees of freedom.

    Returns
    -------
    float
        Variance log ratio value.

    """
    # Mask zeros
    x = np.ma.masked_array(x, mask=x == 0)
    y = np.ma.masked_array(y, mask=y == 0)

    # Log transformation
    x = np.ma.log(x)
    y = np.ma.log(y)

    # Variance log ratio
    return np.ma.var(x - y, ddof=ddof)


@experimental(as_of="0.5.7")
def vlr(x: np.ndarray, y: np.ndarray, ddof: int = 1, robust: bool = False):
    r"""Calculate variance log ratio.

    Parameters
    ----------
    x : array_like, float
        A 1-dimensional vector of proportions.
    y : array_like, float
        A 1-dimensional vector of proportions.
    ddof: int
        Degrees of freedom.
    robust: bool
        Mask zeros at the cost of performance.

    Returns
    -------
    float
        Variance log ratio value.

    Notes
    -----
    Variance log ratio was described in [1]_ and [2]_.

    References
    ----------
    .. [1] V. Lovell D, Pawlowsky-Glahn V, Egozcue JJ, Marguerat S,
           Bähler J (2015) Proportionality: A Valid Alternative to
           Correlation for Relative Data. PLoS Comput Biol 11(3): e1004075.
           https://doi.org/10.1371/journal.pcbi.1004075
    .. [2] Erb, I., Notredame, C.
           How should we measure proportionality on relative gene
           expression data?. Theory Biosci. 135, 21-36 (2016).
           https://doi.org/10.1007/s12064-015-0220-8

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import vlr
    >>> x = np.exp([1,2,3])
    >>> y = np.exp([2,3,4])
    >>> vlr(x,y)  # no zeros
    0.0

    """
    # Convert array_like to numpy array
    x = closure(x)
    y = closure(y)

    # Set up input and parameters
    kwargs = {
        "x": x,
        "y": y,
        "ddof": ddof,
    }

    # Run backend function
    if robust:
        return _robust_vlr(**kwargs)
    else:
        return _vlr(**kwargs)


@experimental(as_of="0.5.7")
def _pairwise_vlr(mat: np.ndarray, ddof: int):
    r"""Perform pairwise variance log ratio transformation.

    Parameters
    ----------
    mat : array_like, float
        a matrix of proportions where
        rows = compositions and
        columns = components
    ids : array_like, str
        Component names.
    ddof : int
        Degrees of freedom.

    Returns
    -------
    skbio.DistanceMatrix
        Distance matrix of variance log ratio values.

    """
    # Log Transform
    X_log = np.log(mat)

    # Variance Log Ratio
    covariance = np.cov(X_log.T, ddof=ddof)
    diagonal = np.diagonal(covariance)
    vlr_data = -2 * covariance + diagonal[:, np.newaxis] + diagonal
    return vlr_data


@experimental(as_of="0.5.7")
def pairwise_vlr(
    mat, ids=None, ddof: int = 1, robust: bool = False, validate: bool = True
):
    r"""Perform pairwise variance log ratio transformation.

    Parameters
    ----------
    mat : array_like, float
        a matrix of proportions where
        rows = compositions and
        columns = components
    ids : array_like, str
        Component names.
    ddof : int
        Degrees of freedom.
    robust : bool
        Mask zeros at the cost of performance.
    validate : bool
        Whether to validate the distance matrix after construction.

    Returns
    -------
    skbio.DistanceMatrix if validate=True
        Distance matrix of variance log ratio values.
    skbio.DissimilarityMatrix if validate=False
        Dissimilarity matrix of variance log ratio values.

    Notes
    -----
    Pairwise variance log ratio transformation was described in [1]_ and [2]_.

    References
    ----------
    .. [1] V. Lovell D, Pawlowsky-Glahn V, Egozcue JJ, Marguerat S,
           Bähler J (2015) Proportionality: A Valid Alternative to
           Correlation for Relative Data. PLoS Comput Biol 11(3): e1004075.
           https://doi.org/10.1371/journal.pcbi.1004075
    .. [2] Erb, I., Notredame, C.
           How should we measure proportionality on relative gene
           expression data?. Theory Biosci. 135, 21-36 (2016).
           https://doi.org/10.1007/s12064-015-0220-8

    Examples
    --------
    >>> import numpy as np
    >>> from skbio.stats.composition import pairwise_vlr
    >>> mat = np.array([np.exp([1, 2, 2]),
    ...                 np.exp([2, 3, 6]),
    ...                 np.exp([2, 3, 12])]).T
    >>> dism = pairwise_vlr(mat)
    >>> dism.redundant_form()
    array([[  0.,   3.,  27.],
           [  3.,   0.,  12.],
           [ 27.,  12.,   0.]])

    """
    # Mask zeros
    mat = closure(mat.astype(np.float64))

    # Set up input and parameters
    kwargs = {
        "mat": mat,
        "ddof": ddof,
    }

    # Variance Log Ratio
    if robust:
        raise NotImplementedError("Pairwise version of robust VLR not implemented.")
    else:
        vlr_data = _pairwise_vlr(**kwargs)

    # Return distance matrix
    if validate:
        vlr_data = 0.5 * (vlr_data + vlr_data.T)
        return DistanceMatrix(vlr_data, ids=ids)

    # Return dissimilarity matrix
    else:
        return DistanceMatrix(vlr_data, ids=ids, validate=False)


@experimental(as_of="0.5.8")
def tree_basis(tree):
    r"""Calculate sparse representation of an ilr basis from a tree.

    This computes an orthonormal basis specified from a bifurcating tree.

    Parameters
    ----------
    tree : skbio.TreeNode
        Input bifurcating tree.  Must be strictly bifurcating
        (i.e. every internal node needs to have exactly 2 children).
        This is used to specify the ilr basis.

    Returns
    -------
    scipy.sparse.coo_matrix
       The ilr basis required to perform the ilr_inv transform.
       This is also known as the sequential binary partition.
       Note that this matrix is represented in clr coordinates.
    nodes : list, str
        List of tree nodes indicating the ordering in the basis.

    Raises
    ------
    ValueError
        The tree doesn't contain two branches.

    Examples
    --------
    >>> from skbio import TreeNode
    >>> tree = u"((b,c)a, d)root;"
    >>> t = TreeNode.read([tree])
    >>> basis, nodes = tree_basis(t)
    >>> basis.toarray()
    array([[-0.40824829, -0.40824829,  0.81649658],
           [-0.70710678,  0.70710678,  0.        ]])

    """
    # Specifies which child is numerator and denominator
    # within any given node in a tree.
    NUMERATOR = 1
    DENOMINATOR = 0
    # this is inspired by @wasade in
    # https://github.com/biocore/gneiss/pull/8
    t = tree.copy()
    D = len(list(tree.tips()))
    # calculate number of tips under each node
    for n in t.postorder(include_self=True):
        if n.is_tip():
            n._tip_count = 1
        else:
            if len(n.children) == 2:
                left, right = (
                    n.children[NUMERATOR],
                    n.children[DENOMINATOR],
                )
            else:
                raise ValueError("Not a strictly bifurcating tree.")
            n._tip_count = left._tip_count + right._tip_count

    # calculate k, r, s, t coordinate for each node
    left, right = (
        t.children[NUMERATOR],
        t.children[DENOMINATOR],
    )
    t._k, t._r, t._s, t._t = 0, left._tip_count, right._tip_count, 0
    for n in t.preorder(include_self=False):
        if n.is_tip():
            n._k, n._r, n._s, n._t = 0, 0, 0, 0

        elif n == n.parent.children[NUMERATOR]:
            n._k = n.parent._k
            n._r = n.children[NUMERATOR]._tip_count
            n._s = n.children[DENOMINATOR]._tip_count
            n._t = n.parent._s + n.parent._t
        elif n == n.parent.children[DENOMINATOR]:
            n._k = n.parent._r + n.parent._k
            n._r = n.children[NUMERATOR]._tip_count
            n._s = n.children[DENOMINATOR]._tip_count
            n._t = n.parent._t
        else:
            raise ValueError("Tree topology is not correct.")

    # navigate through tree to build the basis in a sparse matrix form
    value = []
    row, col = [], []
    nodes = []
    i = 0

    for n in t.levelorder(include_self=True):
        if n.is_tip():
            continue

        for j in range(n._k, n._k + n._r):
            row.append(i)
            # consider tips in reverse order. May want to rethink
            # this orientation in the future.
            col.append(D - 1 - j)
            A = np.sqrt(n._s / (n._r * (n._s + n._r)))

            value.append(A)

        for j in range(n._k + n._r, n._k + n._r + n._s):
            row.append(i)
            col.append(D - 1 - j)
            B = -np.sqrt(n._r / (n._s * (n._s + n._r)))

            value.append(B)
        i += 1
        nodes.append(n.name)

    basis = coo_matrix((value, (row, col)), shape=(D - 1, D))

    return basis, nodes


@experimental(as_of="0.4.1")
def ancom(
    table,
    grouping,
    alpha=0.05,
    tau=0.02,
    theta=0.1,
    multiple_comparisons_correction="holm-bonferroni",
    significance_test=None,
    percentiles=(0.0, 25.0, 50.0, 75.0, 100.0),
):
    r"""Perform a differential abundance test using ANCOM.

    This is done by calculating pairwise log ratios between all features
    and performing a significance test to determine if there is a significant
    difference in feature ratios with respect to the variable of interest.

    In an experiment with only two treatments, this tests the following
    hypothesis for feature :math:`i`

    .. math::

        H_{0i}: \mathbb{E}[\ln(u_i^{(1)})] = \mathbb{E}[\ln(u_i^{(2)})]

    where :math:`u_i^{(1)}` is the mean abundance for feature :math:`i` in the
    first group and :math:`u_i^{(2)}` is the mean abundance for feature
    :math:`i` in the second group.

    Parameters
    ----------
    table : pd.DataFrame
        A 2D matrix of strictly positive values (i.e. counts or proportions)
        where the rows correspond to samples and the columns correspond to
        features.
    grouping : pd.Series
        Vector indicating the assignment of samples to groups.  For example,
        these could be strings or integers denoting which group a sample
        belongs to.  It must be the same length as the samples in `table`.
        The index must be the same on `table` and `grouping` but need not be
        in the same order.
    alpha : float, optional
        Significance level for each of the statistical tests.
        This can can be anywhere between 0 and 1 exclusive.
    tau : float, optional
        A constant used to determine an appropriate cutoff.
        A value close to zero indicates a conservative cutoff.
        This can can be anywhere between 0 and 1 exclusive.
    theta : float, optional
        Lower bound for the proportion for the W-statistic.
        If all W-statistics are lower than theta, then no features
        will be detected to be differentially significant.
        This can can be anywhere between 0 and 1 exclusive.
    multiple_comparisons_correction : {None, 'holm-bonferroni'}, optional
        The multiple comparison correction procedure to run.  If None,
        then no multiple comparison correction procedure will be run.
        If 'holm-boniferroni' is specified, then the Holm-Boniferroni
        procedure [1]_ will be run.
    significance_test : function, optional
        A statistical significance function to test for significance between
        classes.  This function must be able to accept at least two 1D
        array_like arguments of floats and returns a test statistic and a
        p-value. By default ``scipy.stats.f_oneway`` is used.
    percentiles : iterable of floats, optional
        Percentile abundances to return for each feature in each group. By
        default, will return the minimum, 25th percentile, median, 75th
        percentile, and maximum abundances for each feature in each group.

    Returns
    -------
    pd.DataFrame
        A table of features, their W-statistics and whether the null hypothesis
        is rejected.

        `"W"` is the W-statistic, or number of features that a single feature
        is tested to be significantly different against.

        `"Reject null hypothesis"` indicates if feature is differentially
        abundant across groups (`True`) or not (`False`).

    pd.DataFrame
        A table of features and their percentile abundances in each group. If
        ``percentiles`` is empty, this will be an empty ``pd.DataFrame``. The
        rows in this object will be features, and the columns will be a
        multi-index where the first index is the percentile, and the second
        index is the group.

    See Also
    --------
    multiplicative_replacement
    scipy.stats.ttest_ind
    scipy.stats.f_oneway
    scipy.stats.wilcoxon
    scipy.stats.kruskal

    Notes
    -----
    The developers of this method recommend the following significance tests
    ([2]_, Supplementary File 1, top of page 11): if there are 2 groups, use
    the standard parametric t-test (``scipy.stats.ttest_ind``) or
    non-parametric Mann-Whitney rank test (``scipy.stats.mannwhitneyu``).
    For paired samples, use the parametric paired t-test
    (``scipy.stats.ttest_rel``) or nonparametric Wilcoxon signed-rank test
    (``scipy.stats.wilcoxon``). If there are more than 2 groups, use
    parametric one-way ANOVA (``scipy.stats.f_oneway``) or nonparametric
    Kruskal-Wallis (``scipy.stats.kruskal``). If there are multiple
    measurements obtained from the individuals, use a Friedman test
    (``scipy.stats.friedmanchisquare``).  Because one-way ANOVA is
    equivalent to the standard t-test when the number of groups is two, we
    default to ``scipy.stats.f_oneway`` here, which can be used when there
    are two or more groups. Users should refer to the documentation of these
    tests in SciPy to understand the assumptions made by each test.

    This method cannot handle any zero counts as input, since the logarithm
    of zero cannot be computed.  While this is an unsolved problem, many
    studies, including [2]_, have shown promising results by adding
    pseudocounts to all values in the matrix. In [2]_, a pseudocount of 0.001
    was used, though the authors note that a pseudocount of 1.0 may also be
    useful. Zero counts can also be addressed using the
    ``multiplicative_replacement`` method.

    References
    ----------
    .. [1] Holm, S. "A simple sequentially rejective multiple test procedure".
       Scandinavian Journal of Statistics (1979), 6.
    .. [2] Mandal et al. "Analysis of composition of microbiomes: a novel
       method for studying microbial composition", Microbial Ecology in Health
       & Disease, (2015), 26.

    Examples
    --------
    First import all of the necessary modules:

    >>> from skbio.stats.composition import ancom
    >>> import pandas as pd

    Now let's load in a DataFrame with 6 samples and 7 features (e.g.,
    these may be bacterial OTUs):

    >>> table = pd.DataFrame([[12, 11, 10, 10, 10, 10, 10],
    ...                       [9,  11, 12, 10, 10, 10, 10],
    ...                       [1,  11, 10, 11, 10, 5,  9],
    ...                       [22, 21, 9,  10, 10, 10, 10],
    ...                       [20, 22, 10, 10, 13, 10, 10],
    ...                       [23, 21, 14, 10, 10, 10, 10]],
    ...                      index=['s1', 's2', 's3', 's4', 's5', 's6'],
    ...                      columns=['b1', 'b2', 'b3', 'b4', 'b5', 'b6',
    ...                               'b7'])

    Then create a grouping vector. In this example, there is a treatment group
    and a placebo group.

    >>> grouping = pd.Series(['treatment', 'treatment', 'treatment',
    ...                       'placebo', 'placebo', 'placebo'],
    ...                      index=['s1', 's2', 's3', 's4', 's5', 's6'])

    Now run ``ancom`` to determine if there are any features that are
    significantly different in abundance between the treatment and the placebo
    groups. The first DataFrame that is returned contains the ANCOM test
    results, and the second contains the percentile abundance data for each
    feature in each group.

    >>> ancom_df, percentile_df = ancom(table, grouping)
    >>> ancom_df['W']
    b1    0
    b2    4
    b3    0
    b4    1
    b5    1
    b6    0
    b7    1
    Name: W, dtype: int64

    The W-statistic is the number of features that a single feature is tested
    to be significantly different against.  In this scenario, `b2` was detected
    to have significantly different abundances compared to four of the other
    features. To summarize the results from the W-statistic, let's take a look
    at the results from the hypothesis test. The `Reject null hypothesis`
    column in the table indicates whether the null hypothesis was rejected,
    and that a feature was therefore observed to be differentially abundant
    across the groups.

    >>> ancom_df['Reject null hypothesis']
    b1    False
    b2     True
    b3    False
    b4    False
    b5    False
    b6    False
    b7    False
    Name: Reject null hypothesis, dtype: bool

    From this we can conclude that only `b2` was significantly different in
    abundance between the treatment and the placebo. We still don't know, for
    example, in which group `b2` was more abundant. We therefore may next be
    interested in comparing the abundance of `b2` across the two groups.
    We can do that using the second DataFrame that was returned. Here we
    compare the median (50th percentile) abundance of `b2` in the treatment and
    placebo groups:

    >>> percentile_df[50.0].loc['b2']
    Group
    placebo      21.0
    treatment    11.0
    Name: b2, dtype: float64

    We can also look at a full five-number summary for ``b2`` in the treatment
    and placebo groups:

    >>> percentile_df.loc['b2'] # doctest: +NORMALIZE_WHITESPACE
    Percentile  Group
    0.0         placebo      21.0
    25.0        placebo      21.0
    50.0        placebo      21.0
    75.0        placebo      21.5
    100.0       placebo      22.0
    0.0         treatment    11.0
    25.0        treatment    11.0
    50.0        treatment    11.0
    75.0        treatment    11.0
    100.0       treatment    11.0
    Name: b2, dtype: float64

    Taken together, these data tell us that `b2` is present in significantly
    higher abundance in the placebo group samples than in the treatment group
    samples.

    """
    if not isinstance(table, pd.DataFrame):
        raise TypeError(
            "`table` must be a `pd.DataFrame`, " "not %r." % type(table).__name__
        )
    if not isinstance(grouping, pd.Series):
        raise TypeError(
            "`grouping` must be a `pd.Series`," " not %r." % type(grouping).__name__
        )

    if np.any(table <= 0):
        raise ValueError(
            "Cannot handle zeros or negative values in `table`. "
            "Use pseudocounts or ``multiplicative_replacement``."
        )

    if not 0 < alpha < 1:
        raise ValueError("`alpha`=%f is not within 0 and 1." % alpha)

    if not 0 < tau < 1:
        raise ValueError("`tau`=%f is not within 0 and 1." % tau)

    if not 0 < theta < 1:
        raise ValueError("`theta`=%f is not within 0 and 1." % theta)

    if multiple_comparisons_correction is not None:
        if multiple_comparisons_correction != "holm-bonferroni":
            raise ValueError(
                "%r is not an available option for "
                "`multiple_comparisons_correction`." % multiple_comparisons_correction
            )

    if (grouping.isnull()).any():
        raise ValueError("Cannot handle missing values in `grouping`.")

    if (table.isnull()).any().any():
        raise ValueError("Cannot handle missing values in `table`.")

    percentiles = list(percentiles)
    for percentile in percentiles:
        if not 0.0 <= percentile <= 100.0:
            raise ValueError(
                "Percentiles must be in the range [0, 100], %r "
                "was provided." % percentile
            )

    duplicates = skbio.util.find_duplicates(percentiles)
    if duplicates:
        formatted_duplicates = ", ".join(repr(e) for e in duplicates)
        raise ValueError(
            "Percentile values must be unique. The following"
            " value(s) were duplicated: %s." % formatted_duplicates
        )

    groups = np.unique(grouping)
    num_groups = len(groups)

    if num_groups == len(grouping):
        raise ValueError(
            "All values in `grouping` are unique. This method cannot "
            "operate on a grouping vector with only unique values (e.g., "
            "there are no 'within' variance because each group of samples "
            "contains only a single sample)."
        )

    if num_groups == 1:
        raise ValueError(
            "All values the `grouping` are the same. This method cannot "
            "operate on a grouping vector with only a single group of samples"
            "(e.g., there are no 'between' variance because there is only a "
            "single group)."
        )

    if significance_test is None:
        significance_test = scipy.stats.f_oneway

    table_index_len = len(table.index)
    grouping_index_len = len(grouping.index)
    mat, cats = table.align(grouping, axis=0, join="inner")
    if len(mat) != table_index_len or len(cats) != grouping_index_len:
        raise ValueError("`table` index and `grouping` " "index must be consistent.")

    n_feat = mat.shape[1]

    _logratio_mat = _log_compare(mat.values, cats.values, significance_test)
    logratio_mat = _logratio_mat + _logratio_mat.T

    # Multiple comparisons
    if multiple_comparisons_correction == "holm-bonferroni":
        logratio_mat = np.apply_along_axis(_holm_bonferroni, 1, logratio_mat)
    np.fill_diagonal(logratio_mat, 1)
    W = (logratio_mat < alpha).sum(axis=1)
    c_start = W.max() / n_feat
    if c_start < theta:
        reject = np.zeros_like(W, dtype=bool)
    else:
        # Select appropriate cutoff
        cutoff = c_start - np.linspace(0.05, 0.25, 5)
        prop_cut = np.array([(W > n_feat * cut).mean() for cut in cutoff])
        dels = np.abs(prop_cut - np.roll(prop_cut, -1))
        dels[-1] = 0

        if (dels[0] < tau) and (dels[1] < tau) and (dels[2] < tau):
            nu = cutoff[1]
        elif (dels[0] >= tau) and (dels[1] < tau) and (dels[2] < tau):
            nu = cutoff[2]
        elif (dels[1] >= tau) and (dels[2] < tau) and (dels[3] < tau):
            nu = cutoff[3]
        else:
            nu = cutoff[4]
        reject = W >= nu * n_feat

    feat_ids = mat.columns
    ancom_df = pd.DataFrame(
        {
            "W": pd.Series(W, index=feat_ids),
            "Reject null hypothesis": pd.Series(reject, index=feat_ids),
        }
    )

    if len(percentiles) == 0:
        return ancom_df, pd.DataFrame()
    else:
        data = []
        columns = []
        for group in groups:
            feat_dists = mat[cats == group]
            for percentile in percentiles:
                columns.append((percentile, group))
                data.append(np.percentile(feat_dists, percentile, axis=0))
        columns = pd.MultiIndex.from_tuples(columns, names=["Percentile", "Group"])
        percentile_df = pd.DataFrame(
            np.asarray(data).T, columns=columns, index=feat_ids
        )
        return ancom_df, percentile_df


def _holm_bonferroni(p):
    """Perform Holm-Bonferroni correction.

    Perform Holm-Bonferroni correction for pvalues to account for multiple comparisons.

    Parameters
    ----------
    p: numpy.array
        array of pvalues

    Returns
    -------
    numpy.array
        corrected pvalues

    """
    K = len(p)
    sort_index = -np.ones(K, dtype=np.int64)
    sorted_p = np.sort(p)
    sorted_p_adj = sorted_p * (K - np.arange(K))
    for j in range(K):
        idx = (p == sorted_p[j]) & (sort_index < 0)
        num_ties = len(sort_index[idx])
        sort_index[idx] = np.arange(j, (j + num_ties), dtype=np.int64)

    sorted_holm_p = [min([max(sorted_p_adj[:k]), 1]) for k in range(1, K + 1)]
    holm_p = [sorted_holm_p[sort_index[k]] for k in range(K)]
    return holm_p


def _log_compare(mat, cats, significance_test=scipy.stats.ttest_ind):
    """Calculate pairwise log ratios and perform a significance test.

    Calculate pairwise log ratios between all features and perform a
    significance test (i.e. t-test) to determine if there is a significant
    difference in feature ratios with respect to the variable of interest.

    Parameters
    ----------
    mat: np.array
       rows correspond to samples and columns correspond to
       features (i.e. OTUs)
    cats: np.array, float
       Vector of categories
    significance_test: function
        statistical test to run

    Returns
    -------
    log_ratio : np.array
        log ratio pvalue matrix

    """
    r, c = mat.shape
    log_ratio = np.zeros((c, c))
    log_mat = np.log(mat)
    cs = np.unique(cats)

    def func(x):
        return significance_test(*[x[cats == k] for k in cs])

    for i in range(c - 1):
        ratio = (log_mat[:, i].T - log_mat[:, i + 1 :].T).T
        m, p = np.apply_along_axis(func, axis=0, arr=ratio)
        log_ratio[i, i + 1 :] = np.squeeze(np.array(p.T))
    return log_ratio


def _gram_schmidt_basis(n):
    """Build clr transformed basis derived from gram schmidt orthogonalization.

    Parameters
    ----------
    n : int
        Dimension of the Aitchison simplex

    Returns
    -------
    basis : np.array
        Dimension (n-1) x n basis matrix

    """
    basis = np.zeros((n, n - 1))
    for j in range(n - 1):
        i = j + 1
        e = np.array([(1 / i)] * i + [-1] + [0] * (n - i - 1)) * np.sqrt(i / (i + 1))
        basis[:, j] = e
    return basis.T


@experimental(as_of="0.5.5")
def sbp_basis(sbp):
    r"""Build an orthogonal basis from a sequential binary partition (SBP).

    As explained in [1]_, the SBP is a hierarchical collection of binary
    divisions of compositional parts. The child groups are divided again until
    all groups contain a single part. The SBP can be encoded in a
    :math:`(D - 1) \times D` matrix where, for each row, parts can be grouped
    by -1 and +1 tags, and 0 for excluded parts. The `sbp_basis` method was
    originally derived from function `gsi.buildilrBase()` found in the R
    package `compositions` [2]_. The ith balance is computed as follows

    .. math::
        b_i = \sqrt{ \frac{r_i s_i}{r_i+s_i} }
        \ln \left( \frac{g(x_{r_i})}{g(x_{s_i})} \right)

    where :math:`b_i` is the ith balance corresponding to the ith row in the
    SBP, :math:`r_i` and :math:`s_i` and the number of respectively `+1` and
    `-1` labels in the ith row of the SBP and where :math:`g(x) =
    (\prod\limits_{i=1}^{D} x_i)^{1/D}` is the geometric mean of :math:`x`.

    Parameters
    ----------
    sbp: np.array, int
        A contrast matrix, also known as a sequential binary partition, where
        every row represents a partition between two groups of features. A part
        labelled `+1` would correspond to that feature being in the numerator
        of the given row partition, a part labelled `-1` would correspond to
        features being in the denominator of that given row partition, and `0`
        would correspond to features excluded in the row partition.

    Returns
    -------
    numpy.array
        An orthonormal basis in the Aitchison simplex

    Examples
    --------
    >>> import numpy as np
    >>> sbp = np.array([[1, 1,-1,-1,-1],
    ...                 [1,-1, 0, 0, 0],
    ...                 [0, 0, 1,-1,-1],
    ...                 [0, 0, 0, 1,-1]])
    ...
    >>> sbp_basis(sbp)
    array([[ 0.54772256,  0.54772256, -0.36514837, -0.36514837, -0.36514837],
           [ 0.70710678, -0.70710678,  0.        ,  0.        ,  0.        ],
           [ 0.        ,  0.        ,  0.81649658, -0.40824829, -0.40824829],
           [ 0.        ,  0.        ,  0.        ,  0.70710678, -0.70710678]])

    References
    ----------
    .. [1] Parent, S.É., Parent, L.E., Egozcue, J.J., Rozane, D.E.,
       Hernandes, A., Lapointe, L., Hébert-Gentile, V., Naess, K.,
       Marchand, S., Lafond, J., Mattos, D., Barlow, P., Natale, W., 2013.
       The plant ionome revisited by the nutrient balance concept.
       Front. Plant Sci. 4, 39, http://dx.doi.org/10.3389/fpls.2013.00039.
    .. [2] van den Boogaart, K. Gerald, Tolosana-Delgado, Raimon and Bren,
       Matevz, 2014. `compositions`: Compositional Data Analysis. R package
       version 1.40-1. https://CRAN.R-project.org/package=compositions.

    """
    n_pos = (sbp == 1).sum(axis=1)
    n_neg = (sbp == -1).sum(axis=1)
    psi = np.zeros(sbp.shape)
    for i in range(0, sbp.shape[0]):
        psi[i, :] = sbp[i, :] * np.sqrt(
            (n_neg[i] / n_pos[i]) ** sbp[i, :] / np.sum(np.abs(sbp[i, :]))
        )
    return psi


def _check_orthogonality(basis):
    """Check to see if basis is truly orthonormal in the Aitchison simplex.

    Parameters
    ----------
    basis: numpy.ndarray
        basis in the Aitchison simplex of dimension d-1 x d

    """
    basis = np.atleast_2d(basis)
    if not np.allclose(basis @ basis.T, np.identity(len(basis)), rtol=1e-4, atol=1e-6):
        raise ValueError("Basis is not orthonormal")


def _welch_ttest(x1, x2):
    # See https://stats.stackexchange.com/a/475345
    n1 = x1.size
    n2 = x2.size
    m1 = np.mean(x1)
    m2 = np.mean(x2)

    v1 = np.var(x1, ddof=1)
    v2 = np.var(x2, ddof=1)

    pooled_se = np.sqrt(v1 / n1 + v2 / n2)
    delta = m1 - m2

    tstat = delta / pooled_se
    df = (v1 / n1 + v2 / n2) ** 2 / (
        v1**2 / (n1**2 * (n1 - 1)) + v2**2 / (n2**2 * (n2 - 1))
    )

    # two side t-test
    p = 2 * t.cdf(-abs(tstat), df)

    # upper and lower bounds
    lb = delta - t.ppf(0.975, df) * pooled_se
    ub = delta + t.ppf(0.975, df) * pooled_se
    return pd.DataFrame(
        np.array([tstat, df, p, delta, lb, ub]).reshape(1, -1),
        columns=["T statistic", "df", "pvalue", "Difference", "CI(2.5)", "CI(97.5)"],
    )


@experimental(as_of="0.5.9")
def dirmult_ttest(
    table: pd.DataFrame,
    grouping: str,
    treatment: str,
    reference: str,
    pseudocount: float = 0.5,
    draws: int = 128,
    seed=None,
):
    r"""T-test using Dirichilet Mulitnomial Distribution.

    The Dirichlet-multinomial distribution is a compound distribution that
    combines a Dirichlet distribution over the probabilities of a multinomial
    distribution. This distribution is used to model the distribution of
    species abundances in a community.

    To perform the t-test, we first fit a Dirichlet-multinomial distribution
    for each sample, and then we compute the fold change and p-value for each
    feature. The fold change is computed as the difference between the
    samples of the two groups. T-tests are then performed on the posterior
    samples, drawn from each Dirichlet-multinomial distribution. The
    log-fold changes as well as their credible intervals, the pvalues a
    FDR corrected pvalues using Holm-Bonferroni [1]_ are reported.
    This process mirrors the approach performed by ALDEx2.

    Parameters
    ----------
    table : pd.DataFrame
        Contingency table of counts where rows are features and columns are samples.
    grouping : pd.Series
        Vector indicating the assignment of samples to groups.  For example,
        these could be strings or integers denoting which group a sample
        belongs to.  It must be the same length as the samples in `table`.
        The index must be the same on `table` and `grouping` but need not be
        in the same order.  The t-test is computed between the `treatment`
        group and the `reference` group specified in the `grouping` vector.
    treatment : str
        Name of the treatment group.
    reference : str
        Name of the reference group.
    pseudocount : float, optional
        A non-zero value added to the input counts to ensure that all of the
        estimated abundances are strictly greater than zero.
    draws : int, optional
        The number of draws from the Dirichilet-Multinomial posterior distribution
        More draws provide higher uncertainty surrounding the estimated
        log-fold changes and pvalues.
    seed : int or np.random.Generator, optional
        A user-provided random seed or random generator instance.

    Returns
    -------
    pd.DataFrame
        A table of features, their log-fold changes and other relevant statistics.

        `"T statistic"` is the t-statistic outputted from the t-test. T-statistics
        are generated from each posterior draw.  The reported `T statistic` is the
        average across all of the posterior draws.

        `"df"` is the degrees of freedom from the t-test.

        `"Log2(FC)"` is the expected log2-fold change. Within each posterior draw
        the log2 fold-change is computed as the difference between the mean
        log-abundance the `treatment` group and the `reference` group. All log2
        fold changes are expressed in clr coordinates. The reported `Log2(FC)`
        is the average of all of the log2-fold changes computed from each of the
        posterior draws.

        `"CI(2.5)"` is the 2.5% quantile of the log2-fold change. The reported
        `CI(2.5)` is the 2.5% quantile of all of the log2-fold changes computed
        from each of the posterior draws.

        `"CI(97.5)"` is the 97.5% quantile of the log2-fold change. The
        reported `CI(97.5)` is the 97.5% quantile of all of the log2-fold
        changes computed from each of the posterior draws.

        `"pvalue`" is the pvalue of the t-test. The reported `pvalue` is the
        average of all of the pvalues computed from the t-tests calculated
        across all of the posterior draws.

        `qvalue` is the pvalue of the t-test after performing multiple
        hypothesis correction. The reported `qvalue` is computed after
        performing holm-bonferroni multiple hypothesis correction on the
        reported `pvalue`.

        `"Reject null hypothesis"` indicates if feature is differentially
        abundant across groups (`True`) or not (`False`). In order for a
        feature to be differentially abundant, the qvalue needs to be significant
        (i.e. <0.05) and the confidence intervals reported by `CI(2.5)` and
        `CI(97.5)` must not overlap with zero.


    See Also
    --------
    scipy.stats.ttest_ind

    Notes
    -----
    FDR-corrected pvalues use Benjamini-Hochberg for pvalue adjustment for
    multiple corrections. The confidence intervals are computed using the
    mininum 2.5% and maximum 95% bounds computed across all of the posterior draws.

    The reference frame here is the geometric mean. Extracting absolute log
    fold changes from this test assumes that the average feature abundance
    between the `treatment` and the `reference` groups are the same. If this
    assumption is violated, then the log-fold changes will be biased, and the
    pvalues will not be reliable. However, the bias is the same across each
    feature, as a result the ordering of the log-fold changes can still be useful.

    One benefit of using the Dirichlet Multinomial distribution is that the
    statistical power increases with regards to the abundance magnitude. More counts
    per sample will shrink the size of the confidence intervals, and can result in
    lower pvalues.

    References
    ----------
    .. [1] Holm, S. "A simple sequentially rejective multiple test procedure".
       Scandinavian Journal of Statistics (1979), 6.
    .. [2] Fernandes et al. "Unifying the analysis of
       high-throughput sequencing datasets: characterizing RNA-seq,
       16S rRNA gene sequencing and selective growth experiments by
       compositional data analysis." Microbiome (2014).

    Examples
    --------
    >>> import pandas as pd
    >>> from skbio.stats.composition import dirmult_ttest
    >>> table = pd.DataFrame([[20,  110, 100, 101, 100, 103, 104],
    ...                       [33,  110, 120, 100, 101, 100, 102],
    ...                       [12,  110, 100, 110, 100, 50,  90],
    ...                       [202, 201, 9,  10, 10, 11, 11],
    ...                       [200, 202, 10, 10, 13, 10, 10],
    ...                       [203, 201, 14, 10, 10, 13, 12]],
    ...                      index=['s1', 's2', 's3', 's4', 's5', 's6'],
    ...                      columns=['b1', 'b2', 'b3', 'b4', 'b5', 'b6',
    ...                               'b7'])
    >>> grouping = pd.Series(['treatment', 'treatment', 'treatment',
    ...                       'placebo', 'placebo', 'placebo'],
    ...                      index=['s1', 's2', 's3', 's4', 's5', 's6'])
    >>> lfc_result = dirmult_ttest(table, grouping, 'treatment', 'placebo',
    ...                            seed=0)
    >>> lfc_result[["Log2(FC)", "CI(2.5)", "CI(97.5)", "qvalue"]]
        Log2(FC)   CI(2.5)  CI(97.5)    qvalue
    b1 -4.991987 -7.884498 -2.293463  0.020131
    b2 -2.533729 -3.594590 -1.462339  0.007446
    b3  1.627677 -1.048219  4.750792  0.068310
    b4  1.707221 -0.467481  4.164998  0.065613
    b5  1.528243 -1.036910  3.978387  0.068310
    b6  1.182343 -0.702656  3.556061  0.068310
    b7  1.480232 -0.601277  4.043888  0.068310

    """
    rng = get_rng(seed)
    if not isinstance(table, pd.DataFrame):
        raise TypeError(
            "`table` must be a `pd.DataFrame`, " "not %r." % type(table).__name__
        )
    if not isinstance(grouping, pd.Series):
        raise TypeError(
            "`grouping` must be a `pd.Series`," " not %r." % type(grouping).__name__
        )

    if np.any(table < 0):
        raise ValueError("Cannot handle negative values in `table`. ")

    if (grouping.isnull()).any():
        raise ValueError("Cannot handle missing values in `grouping`.")

    if (table.isnull()).any().any():
        raise ValueError("Cannot handle missing values in `table`.")

    table_index_len = len(table.index)
    grouping_index_len = len(grouping.index)
    mat, cats = table.align(grouping, axis=0, join="inner")
    if len(mat) != table_index_len or len(cats) != grouping_index_len:
        raise ValueError("`table` index and `grouping` " "index must be consistent.")

    trt_group = grouping.loc[grouping == treatment]
    ref_group = grouping.loc[grouping == reference]
    posterior = [
        rng.dirichlet(table.values[i] + pseudocount) for i in range(table.shape[0])
    ]
    dir_table = pd.DataFrame(clr(posterior), index=table.index, columns=table.columns)
    res = [
        _welch_ttest(
            np.array(dir_table.loc[trt_group.index, x].values),
            np.array(dir_table.loc[ref_group.index, x].values),
        )
        for x in table.columns
    ]
    res = pd.concat(res)
    for i in range(1, draws):
        posterior = [
            rng.dirichlet(table.values[i] + pseudocount) for i in range(table.shape[0])
        ]
        dir_table = pd.DataFrame(
            clr(posterior), index=table.index, columns=table.columns
        )

        ires = [
            _welch_ttest(
                np.array(dir_table.loc[trt_group.index, x].values),
                np.array(dir_table.loc[ref_group.index, x].values),
            )
            for x in table.columns
        ]
        ires = pd.concat(ires)
        # online average to avoid holding all of the results in memory
        res["Difference"] = (i * res["Difference"] + ires["Difference"]) / (i + 1)
        res["pvalue"] = (i * res["pvalue"] + ires["pvalue"]) / (i + 1)
        res["CI(2.5)"] = np.minimum(res["CI(2.5)"], ires["CI(2.5)"])
        res["CI(97.5)"] = np.maximum(res["CI(97.5)"], ires["CI(97.5)"])
        res["T statistic"] = (i * res["T statistic"] + ires["T statistic"]) / (i + 1)

    res.index = table.columns
    # convert all log fold changes to base 2
    res["Difference"] = res["Difference"] / np.log(2)
    res["CI(2.5)"] = res["CI(2.5)"] / np.log(2)
    res["CI(97.5)"] = res["CI(97.5)"] / np.log(2)

    mres = _holm_bonferroni(res["pvalue"])
    qval = mres

    # test to see if confidence interval includes 0.
    sig = np.logical_or(
        np.logical_and(res["CI(2.5)"] > 0, res["CI(97.5)"] > 0),
        np.logical_and(res["CI(2.5)"] < 0, res["CI(97.5)"] < 0),
    )

    reject = np.logical_and(mres[0], sig)

    res = res.rename(columns={"Difference": "Log2(FC)"})
    res["qvalue"] = qval
    res['"Reject null hypothesis"'] = reject

    col_order = [
        "T statistic",
        "df",
        "Log2(FC)",
        "CI(2.5)",
        "CI(97.5)",
        "pvalue",
        "qvalue",
        '"Reject null hypothesis"',
    ]
    return res[col_order]
