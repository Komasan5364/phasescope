# Phasescope

This application is simple phase scope, just as the name implies.
Also known as phase meter, gonio meter, lissajous meter, etc.

Put it on the edge of your desktop for visual enjoyment, or use for music creation as a monitor, just do as you please!

## Features

- Phase scope
- Panning meter
- Correlation meter
- Adjustable gain (0dB ~ -24dB)
- Sampling from desktop audio or microphone input

## Tested Environments

> [!NOTE]
> OS-dependent operation exists only in PySide6 and soundcard, and both libraries are supported Win/Mac/Linux
>
> So it will probably work on Mac and/or Linux, but we can't guarantee it!

- Windows 10/11
- Python 3.12

## Quick Start

> [!IMPORTANT]
> **Use Python 3.12 if you want to build by [Nuitka](https://github.com/Nuitka/Nuitka).**
>
> This limitation is from Nuitka, does not yet support building with GNU backend due to major structural changes in Python 3.13.
>
> This problem can be avoided by using the MSVC backend, but currently we recommend using Python 3.12

> [!TIP]
> If [uv](https://github.com/astral-sh/uv) is installed, Python 3.12 will automatically download (if not yet installed) and be used, so there is nothing to care.

- Create venv and install dependencies.

```bat
> scripts\setup.bat
```

- Then, execute program.

```bat
> python main.py

or

> uv run python main.py
```

## Building executable

- Basically, Nuitka will do everything about it.

```bat
> scripts\build.bat
```
