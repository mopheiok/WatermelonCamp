import numpy as np


class Node:
    def __init__(self, left, right, rule):
        self.left = left
        self.right = right
        self.feature = rule[0]
        self.threshold = rule[1]


class Leaf:
    def __init__(self, value):
        """
        `value` is an array of class probabilities if classifier is True, else
        the mean of the region
        """
        self.value = value


class DecisionTree:
    def __init__(self,
                 classifier=True,
                 max_depth=None,
                 n_feats=None,
                 criterion="entropy",
                 seed=None,
                 ):
        if seed:
            np.random.seed(seed)

        self.depth = 0
        self.root = None

        self.n_feats = n_feats
        self.criterion = criterion
        self.classifier = classifier
        self.max_depth = max_depth if max_depth else np.inf

        if not classifier and criterion in ["gini", "entropy"]:
            raise ValueError(
                "{} is a valid criterion only when classifier = True.".format(criterion)
            )
        if classifier and criterion == "mse":
            raise ValueError("`mse` is a valid criterion only when classifier = False.")

    def fit(self, X, Y):
        """
        Fit a binary decision tree to a dataset

        Parameters
        ----------
        X : :py:class:`ndarray <numpy.ndarray>` of shape `(N, M)`
            The training data of `N` examples, each with `M` features
        Y : :py:class:`ndarray <numpy.ndarray>` of shape `(N,)`
            An array of integer class labels for each example in `X` if self.classifier = True,
            otherwise the set of target values for each example in `X` 回归模型时呢？
        """
        self.n_classes = max(Y) + 1 if self.classifier else None
        self.n_feats = X.shape[1] if not self.n_feats else min(self.n_feats, X.shape[1])
        self.root = self._grow(X, Y)

    def predict(self, X):
        """
        Use the trained decision tree to classify or predict the examples in `X`
        :param self:
        :param X:
        :return:
        """
        return np.array([self._traverse(x, self.root) for x in X])

    def predict_class_probs(self, X):
        """
        Use the trained decision tree to return the class probabilities for the example in `X`
        :param self:
        :param X:
        :return:
        """
        assert self.classifier, "`predict_class_probs` undefined for classifier = False"
        return np.array([self._traverse(x, self.root, prob=True) for x in X])

    def _grow(self, X, Y, cur_depth=0):
        # if all labels are the same, return a leaf
        if len(set(Y)) == 1:
            if self.classifier:
                prob = np.zeros(self.n_classes)
                prob[Y[0]] = 1.0
            
            return Leaf(prob) if self.classifier else Leaf(Y[0])

        # if we have reached max_depth, return a leaf
        if cur_depth >= self.max_depth:
            v = np.mean(Y, axis=0) # 这个叶子上所有值的均值
            if self.classifier:
                v = np.bincount(Y, minlength=self.n_classes) / len(Y) # 该叶子上每个label的频率
            return Leaf(v)

        cur_depth += 1
        self.depth = max(self.depth, cur_depth)

        # 从M中不重复随机选择n_feats个，而根据之前n_feats的定义 n_feats=M，则是随机排序
        N, M = X.shape
        feat_idxs = np.random.choice(M, self.n_feats, replace=False)

        # greedily select the best split according to `criterion`
        feat, thresh = self._segment(X, Y, feat_idxs)
        l = np.argwhere(X[:, feat] <= thresh).flatten()
        r = np.argwhere(X[:, feat] > thresh).flatten()

        # grow the children that result form the split
        left = self._grow(X[l, :], Y[l], cur_depth)
        right = self._grow(X[r, :], Y[r], cur_depth)
        return Node(left, right, (feat, thresh))

    def _segment(self, X, Y, feat_idxs):
        """
        Find the optimal split rule (feature index and split threshold) for the data 
        according to `self.criterion`
        :param self:
        :param X:
        :param Y:
        :param feat_idxs:
        :return:
        """
        best_gain = -np.inf
        split_idx, split_thresh = None, None
        for i in feat_idxs:
            vals = X[:, i]
            levels = np.unique(vals)
            thresholds = (levels[:-1] + levels[1:]) / 2 if len(levels) > 1 else levels
            gains = np.array([self._impurity_gain(Y, t, vals) for t in thresholds])

            if gains.max() > best_gain:
                split_idx = i
                best_gain = gains.max()
                split_thresh = thresholds[gains.argmax()]

        return split_idx, split_thresh

    def _impurity_gain(self, Y, split_thresh, feat_values):
        """
        compute the impurity gain associated with a given split.
        IG(split) = loss(parent) - weighted_avg[loss(left_child), loss(right_child)]
        :param self:
        :param Y:
        :param split_thresh:
        :param feat_values:
        :return:
        """
        if self.criterion == "entropy":
            loss = entropy
        elif self.criterion == "gini":
            loss = gini
        elif self.criterion == "mse":
            loss = mse

        parent_loss = loss(Y)

        # generate split
        left = np.argwhere(feat_values <= split_thresh).flatten()
        right = np.argwhere(feat_values > split_thresh).flatten()

        if len(left) == 0 or len(right) == 0:
            return 0

        # compute the weighted avg. of the loss for the children
        n = len(Y)
        n_l, n_r = len(left), len(right)
        e_l, e_r = loss(Y[left]), loss(Y[right])
        child_loss = (n_l / n) * e_l + (n_r / n) * e_r

        # impurity gain is difference in loss before vs. after split
        ig = parent_loss - child_loss
        return ig

    def _traverse(self, X, node, prob=False):
        if isinstance(node, Leaf):
            if self.classifier:
                return node.value if prob else node.value.argmax()
            return node.value
        if X[node.feature] <= node.threshold:
            return self._traverse(X, node.left, prob)
        return self._traverse(X, node.right, prob)


def mse(y):
    """

    :param y:
    :return:
    """
    return np.mean((y - np.mean(y)) ** 2)


def entropy(y):
    """

    :param y:
    :return:
    """
    hist = np.bincount(y)  # 统计每个值的频数
    ps = hist / np.sum(hist)  # 计算每个值的频率，即概率
    return -np.sum([p * np.log2(p) for p in ps if p > 0])


def gini(y):
    """

    :param y:
    :return:
    """
    hist = np.bincount(y)
    N = np.sum(hist)
    return 1 - sum([(i / N) ** 2 for i in hist])