class HashPrefixAmbiguousError(ValueError):
    pass


class HashNotFoundError(KeyError):
    pass


class DocNotTrackedError(KeyError):
    pass


class DocAlreadyTrackedError(KeyError):
    pass


class SeveralNodesWithDocError(Exception):

    def __init__(self, message, node_hashes):
        super().__init__(message)
        self.node_hashes = node_hashes


class SeveralAncestorsError(Exception):

    def __init__(self, message, ancestor_node_hashes):
        super().__init__(message)
        self.ancestor_node_hashes = ancestor_node_hashes
