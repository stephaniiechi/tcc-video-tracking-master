#include <python.h>

#include <windows.h>
#include <dshow.h>
#include <comutil.h>

#pragma comment(lib, "strmiids")

struct module_state
{
	PyObject *error;
};

#define GETSTATE(m) ((struct module_state *)PyModule_GetState(m))

#pragma comment(lib, "comsuppwd.lib")

HRESULT EnumerateDevices(REFGUID category, IEnumMoniker **ppEnum)
{
	ICreateDevEnum *pDevEnum;
	HRESULT hr = CoCreateInstance(CLSID_SystemDeviceEnum, NULL,
								  CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&pDevEnum));

	if (SUCCEEDED(hr))
	{
		hr = pDevEnum->CreateClassEnumerator(category, ppEnum, 0);
		if (hr == S_FALSE)
		{
			hr = VFW_E_NOT_FOUND;
		}
		pDevEnum->Release();
	}
	return hr;
}

PyObject *DisplayDeviceInformation(IEnumMoniker *pEnum)
{
	PyObject *pyList = PyList_New(0);

	IMoniker *pMoniker = NULL;

	while (pEnum->Next(1, &pMoniker, NULL) == S_OK)
	{
		IPropertyBag *pPropBag;
		HRESULT hr = pMoniker->BindToStorage(0, 0, IID_PPV_ARGS(&pPropBag));
		if (FAILED(hr))
		{
			pMoniker->Release();
			continue;
		}

		VARIANT var;
		VariantInit(&var);

		hr = pPropBag->Read(L"Description", &var, 0);
		if (FAILED(hr))
		{
			hr = pPropBag->Read(L"FriendlyName", &var, 0);
		}
		if (SUCCEEDED(hr))
		{
			char *pValue = _com_util::ConvertBSTRToString(var.bstrVal);
			hr = PyList_Append(pyList, Py_BuildValue("s", pValue));
			delete[] pValue;
			if (FAILED(hr))
			{
				printf("Failed to append the object item at the end of list list\n");
				return pyList;
			}

			VariantClear(&var);
		}

		hr = pPropBag->Write(L"FriendlyName", &var);

		pPropBag->Release();
		pMoniker->Release();
	}

	return pyList;
}

static PyObject *
getDeviceList(PyObject *self, PyObject *args)
{
	PyObject *pyList = NULL;

	HRESULT hr = CoInitializeEx(NULL, COINIT_MULTITHREADED);
	if (SUCCEEDED(hr))
	{
		IEnumMoniker *pEnum;

		hr = EnumerateDevices(CLSID_VideoInputDeviceCategory, &pEnum);
		if (SUCCEEDED(hr))
		{
			pyList = DisplayDeviceInformation(pEnum);
			pEnum->Release();
		}
		CoUninitialize();
	}

	return pyList;
}

static PyMethodDef Methods[] =
	{
		{"get_devices", getDeviceList, METH_VARARGS, NULL},
		{NULL, NULL, 0, NULL}};

static int device_traverse(PyObject *m, visitproc visit, void *arg)
{
	Py_VISIT(GETSTATE(m)->error);
	return 0;
}

static int device_clear(PyObject *m)
{
	Py_CLEAR(GETSTATE(m)->error);
	return 0;
}

static struct PyModuleDef moduledef = {
	PyModuleDef_HEAD_INIT,
	"video_device_listing",
	NULL,
	sizeof(struct module_state),
	Methods,
	NULL,
	device_traverse,
	device_clear,
	NULL};

#define INITERROR return NULL

PyMODINIT_FUNC
PyInit_video_device_listing(void)
{
	PyObject *module = PyModule_Create(&moduledef);

	if (module == NULL)
		INITERROR;
	struct module_state *st = GETSTATE(module);

	st->error = PyErr_NewException("dbr.Error", NULL, NULL);
	if (st->error == NULL)
	{
		Py_DECREF(module);
		INITERROR;
	}

	return module;
}