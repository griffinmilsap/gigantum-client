from collections.abc import Sequence as SequenceABC
from collections.abc import Mapping as MappingABC
from typing import (TypeVar, Generic, Sequence, Mapping, Optional, Iterator, Any, Iterable, Dict, List, overload)


KT = TypeVar('KT') # Generic Key Type
VT = TypeVar('VT') # Generic Value Type
T = TypeVar('T') # Generic Type

class ImmutableDict(MappingABC, Generic[KT, VT]):
    __slots__ = ('__data',)

    def __init__(self, values: Optional[Mapping[KT, VT]] = None) -> None:
        self.__data: Dict[KT, VT] = {}

        if values:
            self.__data.update(values)

    def __getitem__(self, key: KT) -> VT:
        return self.__data[key]

    def __len__(self) -> int:
        return len(self.__data)

    def __iter__(self) -> Iterator[KT]:
        return iter(self.__data)

    def set(self, key: KT, value: VT) -> 'ImmutableDict[KT, VT]':
        data = self.__data.copy()
        data[key] = value
        return ImmutableDict(data)


class ImmutableList(SequenceABC, Generic[T]):
    """A sequence that doesn't allow modification of the data"""
    __slots__ = ('__data',)

    def __init__(self, values: Optional[Sequence[T]] = None) -> None:
        self.__data: List[T] = []

        if values:
            self.__data.extend(values)

    # DP NOTE: The overload allows for adding multiple type signatures
    @overload
    def __getitem__(self, idx: int) -> T: ...

    @overload
    def __getitem__(self, idx: slice) -> 'ImmutableList[T]': ...

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return ImmutableList(self.__data[idx])
        else:
            return self.__data[idx]

    def __len__(self) -> int:
        return len(self.__data)

    @overload
    def __eq__(self, other: Iterable[T]) -> bool: ...

    @overload
    def __eq__(self, other: Any) -> NotImplemented: ...

    def __eq__(self, other):
        try:
            return self.__data == list(other)
        except TypeError:
            return NotImplemented

    def append(self, value: T) -> 'ImmutableList[T]':
        """Append a new element and return the new ImmutableList"""
        return ImmutableList([*self.__data, value])


class SortedImmutableList(SequenceABC, Generic[T]):
    """A sequence that don't allow modification of the data and is always sorted"""
    __slots__ = ('__data','__sort_kwargs')

    def __init__(self, values: Optional[Sequence[T]] = None, **kwargs) -> None:
        self.__data: List[T] = []

        if values:
            self.__data.extend(sorted(values, **kwargs))

        self.__sort_kwargs = kwargs

    # DP NOTE: The overload allows for adding multiple type signatures
    @overload
    def __getitem__(self, idx: int) -> T: ...

    @overload
    def __getitem__(self, idx: slice) -> 'SortedImmutableList[T]': ...

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return SortedImmutableList(self.__data[idx], **self.__sort_kwargs)
        else:
            return self.__data[idx]

    def __len__(self) -> int:
        return len(self.__data)

    @overload
    def __eq__(self, other: Iterable[T]) -> bool: ...

    @overload
    def __eq__(self, other: Any) -> NotImplemented: ...

    def __eq__(self, other):
        try:
            return self.__data == list(other)
        except TypeError:
            return NotImplemented

    def append(self, value: T) -> 'SortedImmutableList[T]':
        data = sorted([*self.__data, value], **self.__sort_kwargs)
        return SortedImmutableList(data, **self.__sort_kwargs)


def DetailRecordList(values: Optional[Sequence[T]] = None) -> SortedImmutableList[T]:
    """Convienence method for creating a SortedImmutableList of ActivityDetailRecords"""
    return SortedImmutableList(values,
                               key = lambda obj: (obj.show, obj.type.value, obj.importance),
                               reverse = True)

def TextData(sub_type: str, data: str) -> ImmutableDict[str, str]:
    """Convienence method for creating an ImmutableDict containing text mime type data"""
    return ImmutableDict({f'text/{sub_type}': data})
