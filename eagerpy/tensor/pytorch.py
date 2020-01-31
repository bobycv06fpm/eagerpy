import numpy as np
from collections.abc import Iterable
from typing import Tuple, cast, Union, Any, TypeVar, TYPE_CHECKING
from importlib import import_module

from .tensor import istensor

from .base import BaseTensor
from .base import unwrap_

if TYPE_CHECKING:
    import torch  # for static analyzers
else:
    # lazy import in PyTorchTensor
    torch = None


# stricter TensorType to get additional type information from the raw method
TensorType = TypeVar("TensorType", bound="PyTorchTensor")


def assert_bool(x: TensorType) -> None:
    if not istensor(x):
        return
    if x.dtype != torch.bool:
        raise ValueError(f"requires dtype bool, consider t.bool().all()")


class PyTorchTensor(BaseTensor):
    def __init__(self, raw: "torch.Tensor"):
        global torch
        if torch is None:
            torch = import_module("torch")
        super().__init__(raw)

    @property
    def raw(self) -> "torch.Tensor":
        return cast(torch.Tensor, super().raw)

    def tanh(self: TensorType) -> TensorType:
        return type(self)(torch.tanh(self.raw))

    def numpy(self: TensorType) -> Any:
        return self.raw.detach().cpu().numpy()

    def item(self) -> Union[int, float, bool]:
        return self.raw.item()

    @property
    def shape(self) -> Tuple:
        return self.raw.shape

    def reshape(self: TensorType, shape) -> TensorType:
        return type(self)(self.raw.reshape(shape))

    def astype(self: TensorType, dtype) -> TensorType:
        return type(self)(self.raw.to(dtype))

    def clip(self: TensorType, min_, max_) -> TensorType:
        return type(self)(self.raw.clamp(min_, max_))

    def square(self: TensorType) -> TensorType:
        return type(self)(self.raw ** 2)

    def arctanh(self: TensorType) -> TensorType:
        """
        improve once this issue has been fixed:
        https://github.com/pytorch/pytorch/issues/10324
        """
        return type(self)(0.5 * (torch.log1p(self.raw) - torch.log1p(-self.raw)))

    def sum(self: TensorType, axis=None, keepdims=False) -> TensorType:
        if axis is None and not keepdims:
            return type(self)(self.raw.sum())
        if axis is None:
            axis = tuple(range(self.ndim))
        return type(self)(self.raw.sum(dim=axis, keepdim=keepdims))

    def mean(self: TensorType, axis=None, keepdims=False) -> TensorType:
        if axis is None and not keepdims:
            return type(self)(self.raw.mean())
        if axis is None:
            axis = tuple(range(self.ndim))
        return type(self)(self.raw.mean(dim=axis, keepdim=keepdims))

    def min(self: TensorType, axis=None, keepdims=False) -> TensorType:
        """
        simplify once this issue has been fixed:
        https://github.com/pytorch/pytorch/issues/28213
        """
        if axis is None and not keepdims:
            return type(self)(self.raw.min())
        if axis is None:
            axis = tuple(range(self.ndim))
        elif not isinstance(axis, Iterable):
            axis = (axis,)
        axis = reversed(sorted(axis))
        x = self.raw
        for i in axis:
            x, _ = x.min(i, keepdim=keepdims)
        return type(self)(x)

    def max(self: TensorType, axis=None, keepdims=False) -> TensorType:
        """
        simplify once this issue has been fixed:
        https://github.com/pytorch/pytorch/issues/28213
        """
        if axis is None and not keepdims:
            return type(self)(self.raw.max())
        if axis is None:
            axis = tuple(range(self.ndim))
        elif not isinstance(axis, Iterable):
            axis = (axis,)
        axis = reversed(sorted(axis))
        x = self.raw
        for i in axis:
            x, _ = x.max(i, keepdim=keepdims)
        return type(self)(x)

    def minimum(self: TensorType, other) -> TensorType:
        if istensor(other):
            other = other.raw
        else:
            other = torch.ones_like(self.raw) * other
        return type(self)(torch.min(self.raw, other))

    def maximum(self: TensorType, other) -> TensorType:
        if istensor(other):
            other = other.raw
        else:
            other = torch.ones_like(self.raw) * other
        return type(self)(torch.max(self.raw, other))

    def argmin(self: TensorType, axis=None) -> TensorType:
        return type(self)(self.raw.argmin(dim=axis))

    def argmax(self: TensorType, axis=None) -> TensorType:
        return type(self)(self.raw.argmax(dim=axis))

    def argsort(self: TensorType, axis=-1) -> TensorType:
        return type(self)(self.raw.argsort(dim=axis))

    def uniform(self: TensorType, shape, low=0.0, high=1.0) -> TensorType:
        return type(self)(
            torch.rand(shape, dtype=self.raw.dtype, device=self.raw.device)
            * (high - low)
            + low
        )

    def normal(self: TensorType, shape, mean=0.0, stddev=1.0) -> TensorType:
        return type(self)(
            torch.randn(shape, dtype=self.raw.dtype, device=self.raw.device) * stddev
            + mean
        )

    def ones(self: TensorType, shape) -> TensorType:
        return type(self)(
            torch.ones(shape, dtype=self.raw.dtype, device=self.raw.device)
        )

    def zeros(self: TensorType, shape) -> TensorType:
        return type(self)(
            torch.zeros(shape, dtype=self.raw.dtype, device=self.raw.device)
        )

    def ones_like(self: TensorType) -> TensorType:
        return type(self)(torch.ones_like(self.raw))

    def zeros_like(self: TensorType) -> TensorType:
        return type(self)(torch.zeros_like(self.raw))

    def full_like(self: TensorType, fill_value) -> TensorType:
        return type(self)(torch.full_like(self.raw, fill_value))

    def onehot_like(self: TensorType, indices: TensorType, *, value=1) -> TensorType:
        if self.ndim != 2:
            raise ValueError("onehot_like only supported for 2D tensors")
        if indices.ndim != 1:
            raise ValueError("onehot_like requires 1D indices")
        if len(indices) != len(self):
            raise ValueError("length of indices must match length of tensor")
        x = torch.zeros_like(self.raw)
        rows = np.arange(x.shape[0])
        x[rows, indices.raw] = value
        return type(self)(x)

    def from_numpy(self: TensorType, a) -> TensorType:
        return type(self)(torch.as_tensor(a, device=self.raw.device))

    def _concatenate(self: TensorType, tensors, axis=0) -> TensorType:
        # concatenates only "tensors", but not "self"
        tensors = unwrap_(tensors)
        return type(self)(torch.cat(tensors, dim=axis))

    def _stack(self: TensorType, tensors, axis=0) -> TensorType:
        # stacks only "tensors", but not "self"
        tensors = unwrap_(tensors)
        return type(self)(torch.stack(tensors, dim=axis))

    def transpose(self: TensorType, axes=None) -> TensorType:
        if axes is None:
            axes = tuple(range(self.ndim - 1, -1, -1))
        return type(self)(self.raw.permute(*axes))

    def bool(self: TensorType) -> TensorType:
        return self.astype(torch.bool)

    def all(self: TensorType, axis=None, keepdims=False) -> TensorType:
        assert_bool(self)
        if axis is None and not keepdims:
            return type(self)(self.raw.all())
        if axis is None:
            axis = tuple(range(self.ndim))
        elif not isinstance(axis, Iterable):
            axis = (axis,)
        axis = reversed(sorted(axis))
        x = self.raw
        for i in axis:
            x = x.all(i, keepdim=keepdims)
        return type(self)(x)

    def any(self: TensorType, axis=None, keepdims=False) -> TensorType:
        assert_bool(self)
        if axis is None and not keepdims:
            return type(self)(self.raw.any())
        if axis is None:
            axis = tuple(range(self.ndim))
        elif not isinstance(axis, Iterable):
            axis = (axis,)
        axis = reversed(sorted(axis))
        x = self.raw
        for i in axis:
            x = x.any(i, keepdim=keepdims)
        return type(self)(x)

    def logical_and(self: TensorType, other) -> TensorType:
        assert_bool(self)
        assert_bool(other)
        return type(self)(self.raw & unwrap_(other))

    def logical_or(self: TensorType, other) -> TensorType:
        assert_bool(self)
        assert_bool(other)
        return type(self)(self.raw | unwrap_(other))

    def logical_not(self: TensorType) -> TensorType:
        assert_bool(self)
        return type(self)(~self.raw)

    def exp(self: TensorType) -> TensorType:
        return type(self)(torch.exp(self.raw))

    def log(self: TensorType) -> TensorType:
        return type(self)(torch.log(self.raw))

    def log2(self: TensorType) -> TensorType:
        return type(self)(torch.log2(self.raw))

    def log10(self: TensorType) -> TensorType:
        return type(self)(torch.log10(self.raw))

    def log1p(self: TensorType) -> TensorType:
        return type(self)(torch.log1p(self.raw))

    def tile(self: TensorType, multiples) -> TensorType:
        multiples = unwrap_(multiples)
        if len(multiples) != self.ndim:
            raise ValueError("multiples requires one entry for each dimension")
        return type(self)(self.raw.repeat(multiples))

    def softmax(self: TensorType, axis=-1) -> TensorType:
        return type(self)(torch.nn.functional.softmax(self.raw, dim=axis))

    def log_softmax(self: TensorType, axis=-1) -> TensorType:
        return type(self)(torch.nn.functional.log_softmax(self.raw, dim=axis))

    def squeeze(self: TensorType, axis=None) -> TensorType:
        if axis is None:
            return type(self)(self.raw.squeeze())
        if not isinstance(axis, Iterable):
            axis = (axis,)
        axis = reversed(sorted(axis))
        x = self.raw
        for i in axis:
            x = x.squeeze(dim=i)
        return type(self)(x)

    def expand_dims(self: TensorType, axis=None) -> TensorType:
        return type(self)(self.raw.unsqueeze(dim=axis))

    def full(self: TensorType, shape, value) -> TensorType:
        if not isinstance(shape, Iterable):
            shape = (shape,)
        return type(self)(
            torch.full(shape, value, dtype=self.raw.dtype, device=self.raw.device)
        )

    def index_update(self: TensorType, indices, values) -> TensorType:
        indices, values = unwrap_(indices, values)
        if isinstance(indices, tuple):
            indices = unwrap_(indices)
        x = self.raw.clone()
        x[indices] = values
        return type(self)(x)

    def arange(self: TensorType, start, stop=None, step=None) -> TensorType:
        if step is None:
            step = 1
        if stop is None:
            stop = start
            start = 0
        return type(self)(
            torch.arange(start=start, end=stop, step=step, device=self.raw.device)
        )

    def cumsum(self: TensorType, axis=None) -> TensorType:
        if axis is None:
            return type(self)(self.raw.reshape(-1).cumsum(dim=0))
        return type(self)(self.raw.cumsum(dim=axis))

    def flip(self: TensorType, axis=None) -> TensorType:
        if axis is None:
            axis = tuple(range(self.ndim))
        if not isinstance(axis, Iterable):
            axis = (axis,)
        return type(self)(self.raw.flip(dims=axis))

    def meshgrid(self: TensorType, *tensors, indexing="xy") -> Tuple[TensorType, ...]:
        tensors = unwrap_(tensors)
        if indexing == "ij" or len(tensors) == 0:
            outputs = torch.meshgrid(self.raw, *tensors)
        elif indexing == "xy":
            outputs = torch.meshgrid(tensors[0], self.raw, *tensors[1:])
        else:
            raise ValueError(  # pragma: no cover
                f"Valid values for indexing are 'xy' and 'ij', got {indexing}"
            )
        results = [type(self)(out) for out in outputs]
        if indexing == "xy" and len(results) >= 2:
            results[0], results[1] = results[1], results[0]
        return tuple(results)

    def pad(self: TensorType, paddings, mode="constant", value=0) -> TensorType:
        if len(paddings) != self.ndim:
            raise ValueError("pad requires a tuple for each dimension")
        for p in paddings:
            if len(p) != 2:
                raise ValueError("pad requires a tuple for each dimension")
        if not (mode == "constant" or mode == "reflect"):
            raise ValueError("pad requires mode 'constant' or 'reflect'")
        if mode == "reflect":
            # PyTorch's pad has limited support for 'reflect' padding
            if self.ndim != 3 and self.ndim != 4:
                raise NotImplementedError  # pragma: no cover
            k = self.ndim - 2
            if paddings[:k] != ((0, 0),) * k:
                raise NotImplementedError  # pragma: no cover
            paddings = paddings[k:]
        paddings = tuple(x for p in reversed(paddings) for x in p)
        return type(self)(
            torch.nn.functional.pad(self.raw, paddings, mode=mode, value=value)
        )

    def isnan(self: TensorType) -> TensorType:
        return type(self)(torch.isnan(self.raw))

    def isinf(self: TensorType) -> TensorType:
        return type(self)(torch.isinf(self.raw))

    def crossentropy(self: TensorType, labels: TensorType) -> TensorType:
        if self.ndim != 2:
            raise ValueError("crossentropy only supported for 2D logits tensors")
        if self.shape[:1] != labels.shape:
            raise ValueError("labels must be 1D and must match the length of logits")
        return type(self)(
            torch.nn.functional.cross_entropy(self.raw, labels.raw, reduction="none")
        )

    def _value_and_grad_fn(self: TensorType, f, has_aux=False) -> Any:
        def value_and_grad(
            x: TensorType, *args, **kwargs
        ) -> Union[Tuple[TensorType, TensorType], Tuple[TensorType, Any, TensorType]]:
            x = type(self)(x.raw.clone().requires_grad_())
            if has_aux:
                loss, aux = f(x, *args, **kwargs)
            else:
                loss = f(x, *args, **kwargs)
            loss = loss.raw
            loss.backward()
            assert x.raw.grad is not None
            grad = type(self)(x.raw.grad)
            assert grad.shape == x.shape
            loss = loss.detach()
            loss = type(self)(loss)
            if has_aux:
                if isinstance(aux, PyTorchTensor):
                    aux = PyTorchTensor(aux.raw.detach())
                elif isinstance(aux, tuple):
                    aux = tuple(
                        PyTorchTensor(t.raw.detach())
                        if isinstance(t, PyTorchTensor)
                        else t
                        for t in aux
                    )
                return loss, aux, grad
            else:
                return loss, grad

        return value_and_grad

    def sign(self: TensorType) -> TensorType:
        return type(self)(torch.sign(self.raw))

    def sqrt(self: TensorType) -> TensorType:
        return type(self)(torch.sqrt(self.raw))

    def float32(self: TensorType) -> TensorType:
        return self.astype(torch.float32)

    def where(self: TensorType, x, y) -> TensorType:
        x, y = unwrap_(x, y)
        return type(self)(torch.where(self.raw, x, y))

    def matmul(self: TensorType, other) -> TensorType:
        if self.ndim != 2 or other.ndim != 2:
            raise ValueError(
                f"matmul requires both tensors to be 2D, got {self.ndim}D and {other.ndim}D"
            )
        return type(self)(torch.matmul(self.raw, other.raw))

    def __lt__(self: TensorType, other) -> TensorType:
        return type(self)(self.raw.__lt__(unwrap_(other)))

    def __le__(self: TensorType, other) -> TensorType:
        return type(self)(self.raw.__le__(unwrap_(other)))

    def __eq__(self: TensorType, other) -> TensorType:  # type: ignore
        return type(self)(self.raw.__eq__(unwrap_(other)))

    def __ne__(self: TensorType, other) -> TensorType:  # type: ignore
        return type(self)(self.raw.__ne__(unwrap_(other)))

    def __gt__(self: TensorType, other) -> TensorType:
        return type(self)(self.raw.__gt__(unwrap_(other)))

    def __ge__(self: TensorType, other) -> TensorType:
        return type(self)(self.raw.__ge__(unwrap_(other)))

    def __getitem__(self: TensorType, index) -> TensorType:
        if isinstance(index, tuple):
            index = tuple(x.raw if istensor(x) else x for x in index)
        elif istensor(index):
            index = index.raw
        return type(self)(self.raw[index])
