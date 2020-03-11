import typing
import re
from JAbs import SelectedJVMInitializer, ClassPathT, ClassesImportSpecT
from collections import OrderedDict, defaultdict
import warnings

import sys

decodeScalaSignature = None

class _ScalaMutableWrapper:
	__slots__ = ("_ctor", "_data")
	
	def __init__(self, ji, o, template=None, ctor=None, data=None):
		if ctor is None:
			ctor = o.__class__
		
		if data is None:
			if template:
				data = type(template)(template)
			else:
				data = ji.getSomeKindOfImmutableObjectTemplate(o.__class__)

			for p in data.keys():
				v = getattr(o, p)()
				data[p] = ji.scalaWrapSomeKindOfImmutableObject(v)
		
		self.__class__._data.__set__(self, data)
		self.__class__._ctor.__set__(self, ctor)

	def _revertIter_(self):
		for v in self._revertIter():
			if isinstance(v, __class__):
				v = v._revert()
			yield v

	def _revert(self):
		return self._ctor(list(self._revertIter()))

	def __repr__(self):
		return self.__class__.__name__ + "<" + self._ctor.__name__ + ">(" + repr(self._data) + ")"


class ScalaMutableWrapper(_ScalaMutableWrapper):
	__slots__ = ()

	def _revertIter(self):
		return self._data.values()

	def _revert(self):
		return self._ctor(*tuple(self._revertIter_()))

	def __getattr__(self, k):
		return self._data[k]

	def __setattr__(self, k, v):
		self._data[k] = v

	def __dir__(self):
		return self._data.keys()



class ScalaCollectionMutableWrapper(_ScalaMutableWrapper):
	__slots__ = ()
	
	def __init__(self, ji, o, template=None, ctor=None, data=None):
		super().__init__(ji, o, ctor=ji.scalaSeq, data=[ji.scalaWrapSomeKindOfImmutableObject(el) for el in ji.JavaConverters.asJavaCollection(o)])

	def __getitem__(self, k):
		return self._data[k]

	def __setitem__(self, k, v):
		self._data[k] = v

	def _revertIter(self):
		return self._data

	def _revert(self):
		return self._ctor(list(self._revertIter_()))




class ScalaJVMInitializer:
	__slots__ = ("ji", "scalaVersion")
	def __init__(self, classPathz: ClassPathT, classes2import: ClassesImportSpecT) -> None:
		self.__class__.ji.__set__(self, SelectedJVMInitializer(classPathz, classes2import))
		self.loadScala()

	def __getattr__(self, k):
		return getattr(self.ji, k)

	def __setattr__(self, k, v):
		setattr(self.ji, k, v)

	def loadScala(self) -> None:
		self.ji.ImmutArraySeq = None
		self.loadClasses((
			("scala.util.Properties", "ScalaProps"),
			"scala.concurrent.Await",
			"scala.collection.Iterable",
			"scala.collection.mutable.Seq",
			"scala.collection.mutable.ListBuffer",
			("scala.collection.mutable.ArraySeq", "MutArraySeq"),
			("scala.collection.immutable.HashMap", "ImmutHashMap"),
			("scala.collection.mutable.HashMap", "MutHashMap"),
			"scala.collection.JavaConverters",
			"scala.Some",
			("scala.None", "none"),
			("scala.Predef$", "scalaPredef"),
			("scala.collection.Seq$", "scalaCollSeq"),
			"java.util.Arrays"
		))

		self.scalaVersion = tuple(int(el) for el in str(self.ScalaProps.versionNumberString()).split("."))

		if self.scalaVersion > (2, 13):
			self.loadClasses(
				("scala.collection.immmutable.ArraySeq", "ImmutArraySeq")
			)
		else:
			warnings.warn("Using mutable ArraySeq instead of immutable one, since immutable is not present in this version of Scala " + repr(self.scalaVersion))

		self.scalaPredef = getattr(self.scalaPredef, "MODULE$")
		self.scalaCollSeq = getattr(self.scalaCollSeq, "MODULE$")

	def getScalaSignatureAnnotation(self, scalaClass) -> typing.Any:
		return self.__class__.getScalaSignatureAnnotationFromReflectedClass(self.reflectClass(scalaClass))

	@classmethod
	def getScalaSignatureAnnotationFromReflectedClass(cls, classRefl) -> typing.Any:
		for annot in classRefl.annotations:
			if annot.annotationType().name == "scala.reflect.ScalaSignature":
				return annot
		return None

	def _ensureScalaSignatureBytesDecoderLazyLoaded(self):
		global decodeScalaSignature
		if decodeScalaSignature is None:
			try:
				from .scalaTransformArray import decode as decodeScalaSignaturePython

				def decodeScalaSignature(s: bytes) -> bytes:
					s = bytearray(bytes(s))
					l = decodeScalaSignaturePython(s)
					return bytes(s[:l])


			except ImportError:
				ByteCodecs = ji.loadClass("scala.reflect.internal.pickling.ByteCodecs")

				def decodeScalaSignature(s: bytes) -> bytes:
					l = ByteCodecs.decode(s)
					s = bytes(s)
					return s[:l]

	def getScalaSignatureAnnotationBytes(self) -> bytes:
		self._ensureScalaSignatureBytesDecoderLazyLoaded()
		scalaSignAnnot = self.getScalaSignatureAnnotation(classRefl)
		if scalaSignAnnot:
			s = scalaSignAnnot.bytes().getBytes("UTF-8")
			return decodeScalaSignature(s)

	def scalaMap(self, m, mutable=False):
		if mutable:
			ctor = self.MutHashMap
		else:
			ctor = self.ImmutHashMap

		seq = ctor(len(m))
		for k, v in m.items():
			seq.update(k, v)
		return seq

	def scalaArrSeq(self, it, mutable=True):
		it = list(it)
		if mutable or self.ImmutArraySeq is None:
			ctor = self.MutArraySeq
		else:
			ctor = self.ImmutArraySeq

		seq = ctor(len(it))
		for k, v in enumerate(it):
			seq.update(k, v)
		return seq

	def scalaSet(self, it, mutable=True):
		return self.scalaArrSeq(it, mutable=mutable).toSet()

	def scalaSeq(self, it):
		print("it", it)
		coll = self.scalaCollSeq.apply(self.scalaPredef.wrapRefArray(list(it)))
		coll = coll.to(self.scalaCollSeq.canBuildFrom())
		print("coll", coll)
		print("coll.__class__.__name__", coll.__class__.__name__)
		return coll
		#return self.scalaCollSeq.apply(self.scalaPredef.wrapRefArray(list(it)))
		#return self.scalaPredef.wrapRefArray(list(it))
		#return self.JavaConverters.collectionAsScalaIterable(self.Arrays.asList(list(it))).toSeq()

	scalaTupleRx = re.compile("^_(\\d+)$")

	@classmethod
	def scalaDetuple(cls, t):
		res = [None] * t.productArity()
		for n in dir(t):
			m = cls.scalaTupleRx.match(n)
			if m is not None:
				res[int(m.group(1)) - 1] = getattr(t, n)()
		return tuple(res)

	@staticmethod
	def getSomeKindOfImmutableObjectTemplate(cls):
		c = max(cls.class_.getConstructors(), key=lambda ct: len(ct.getParameters()))
		return OrderedDict([(str(p.getName()), None) for p in c.getParameters()])

	def scalaWrapSomeKindOfImmutableObject(self, o, template=None):
		if not isinstance(o, (str, self.String, int, float, bool, type(None))):
			#print(o.__class__, isinstance(o, self.Iterable), o.__class__.__mro__)
			if isinstance(o, self.Iterable):
				return ScalaCollectionMutableWrapper(self, o)
			else:
				if hasattr(o, "copy$default$1"):
					o = ScalaMutableWrapper(self, o)
				return o
		else:
			return o
