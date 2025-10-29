###############################################################
%global product_name_lower quipucords
%global product_name_title Quipucords
%global server_image quay.io/quipucords/quipucords:2.2
%global ui_image quay.io/quipucords/quipucords-ui:2.2
###############################################################

%global version_ctl 2.2.0
%global templates_dir src/quipucordsctl/templates
%global product_name_upper %(echo %{product_name_lower} | tr '[:lower:]' '[:upper:]')

###############################################################
# Build notes:
# - We officially support RHEL 8 and RHEL 9 downstream but we
#   also build on RHEL 10.
# - The pyproject-rpm-macros is not provided on RHEL 8
#   by default so we leverage the older py3_build and
#   py3_install. For this, we provide a skeleton setup.py that
#   pulls in all that it needs from the pyproject.toml file via
#   setuptools.
# - We also build on Fedora 41 and Fedora 42 with Python 3.13
# - We can also build on Fedora 43, which runs with Python 3.14
#   but that requires bumping the Python requirements for
#   quipucords, cli and installer to include Python 3.14 as we
#   only currently support up through 3.13.
###############################################################

%if 0%{?fedora} >= 43
    %global python3_pkgversion  3.14
    %global __python3 /usr/bin/python3.14
%else
    %if 0%{?fedora} >= 41
        %global python3_pkgversion  3.13
        %global __python3 /usr/bin/python3.13
    %else
        %global python3_pkgversion  3.12
        %global __python3 /usr/bin/python3.12
    %endif
%endif

Name:           %{product_name_lower}ctl
Summary:        installer for %{product_name_lower} server

Version:        %{version_ctl}
Release:        1%{?dist}
Epoch:          0

License:        GPLv3
URL:            https://github.com/quipucords/quipucordsctl
Source0:        %{url}/archive/%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  sed
# Note: for RHEL 8 pyproject-rpm-macros is not available,
#       for RHEL 8 and 9 we build using the older py3_build and py3_install.
%if 0%{?fedora} >= 41 || 0%{?rhel} >= 10
BuildRequires:  pyproject-rpm-macros
%endif
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-wheel
BuildRequires:  python%{python3_pkgversion}-setuptools
%if 0%{?rhel} == 8
# Note: On RHEL 8, the default python3-babel's /usr/bin/pybabel command cannot
#       compile uninstalled locales, so 'test' could not be compiled.
#       A newer version of pybabel (2.7.0+) needs to be installed and that
#       is available via the python38-babel RPM.
#
#       The /usr/bin/pybabel-3.8 command is in the python38-babel RPM and there
#       is no corresponding babel RPM to install.
BuildRequires:  python38-babel
%global __pybabel /usr/bin/pybabel-3.8
%else
BuildRequires:  python3-babel
# Note: python3-babel does not provide the /usr/bin/pybabel binary outside
#       a virtual environment when building in COPR for all releases.
#
#       We need to include the babel package to enable this for us.
BuildRequires:  babel
%global __pybabel /usr/bin/pybabel
%endif

Requires:       bash
Requires:       coreutils
Requires:       podman >= 4.9.4
Requires:       python3-pyxdg
Requires:       python%{python3_pkgversion}
Requires:       python%{python3_pkgversion}-setuptools


%description
%{name} installs and manages the %{product_name_title} server
via systemd using Podman Quadlet services.

%prep
# Note: this must match the GitHub repo name. Do not substitute variables.
%autosetup -n quipucordsctl-%{version}

%build
sed -i \
  -e 's/^quipucordsctl = "quipucordsctl.__main__:main"$/%{name} = "quipucordsctl.__main__:main"/' \
  -e 's/^version = "0.1.0"$/version = "%{version}"/' \
  %{_builddir}/quipucordsctl-%{version}/pyproject.toml
sed -i -E \
  -e 's/^(PROGRAM_NAME\s*=\s*)"[^\"]*"(.*)$/\1"%{name}"\2/' \
  -e 's/^(SERVER_SOFTWARE_PACKAGE\s*=\s*)"[^\"]*"(.*)$/\1"%{product_name_lower}"\2/' \
  -e 's/^(SERVER_SOFTWARE_NAME\s*=\s*)"[^\"]*"(.*)$/\1"%{product_name_title}"\2/' \
  -e 's/^(ENV_VAR_PREFIX\s*=\s*)"[^\"]*"(.*)$/\1"%{product_name_upper}_"\2/' \
  %{_builddir}/quipucordsctl-%{version}/src/quipucordsctl/settings.py
python%{python3_pkgversion} -m ensurepip
python%{python3_pkgversion} -m pip install wheel setuptools
python3 scripts/translations.py --pybabel %{__pybabel} compile

%if 0%{?rhel} == 8 || 0%{?rhel} == 9
    %py3_build
%else
    %pyproject_wheel
%endif

%install
%if 0%{?rhel} == 8 || 0%{?rhel} == 9
    %py3_install
%else
    %pyproject_install
%endif

mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{_datadir}/%{name}/env
cp %{templates_dir}/env/*.env %{buildroot}/%{_datadir}/%{name}/env/

# Copy and rename original source files with appropriate branding.
mkdir -p %{buildroot}/%{_datadir}/%{name}/config
cp %{templates_dir}/config/quipucords-app.container %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-app.container
cp %{templates_dir}/config/quipucords-celery-worker.container %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-celery-worker.container
cp %{templates_dir}/config/quipucords-db.container %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-db.container
cp %{templates_dir}/config/quipucords-redis.container %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-redis.container
cp %{templates_dir}/config/quipucords-server.container %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-server.container
cp %{templates_dir}/config/quipucords.network %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}.network

# Update source files contents with appropriate branding.
sed -i 's/Quipucords/%{product_name_title}/g;s/quipucords/%{product_name_lower}/g' %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}*
sed -i 's/Quipucords/%{product_name_title}/g;s/quipucords/%{product_name_lower}/g' %{buildroot}/%{_datadir}/%{name}/env/*

# Inject specific image versions into the container files.
sed -i 's#^Image=.*#Image=%{server_image}#g' %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-server.container
sed -i 's#^Image=.*#Image=%{server_image}#g' %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-celery-worker.container
sed -i 's#^Image=.*#Image=%{ui_image}#g' %{buildroot}/%{_datadir}/%{name}/config/%{product_name_lower}-app.container

%files
%license LICENSE
%doc README.md
%{_bindir}/%{name}
%{_datadir}/%{name}/config/%{product_name_lower}.network
%{_datadir}/%{name}/config/%{product_name_lower}-app.container
%{_datadir}/%{name}/config/%{product_name_lower}-celery-worker.container
%{_datadir}/%{name}/config/%{product_name_lower}-db.container
%{_datadir}/%{name}/config/%{product_name_lower}-redis.container
%{_datadir}/%{name}/config/%{product_name_lower}-server.container
%{_datadir}/%{name}/env/env-ansible.env
%{_datadir}/%{name}/env/env-app.env
%{_datadir}/%{name}/env/env-celery-worker.env
%{_datadir}/%{name}/env/env-db.env
%{_datadir}/%{name}/env/env-redis.env
%{_datadir}/%{name}/env/env-server.env
%{python3_sitelib}/quipucordsctl/
%if 0%{?rhel} == 8 || 0%{?rhel} == 9
  %{python3_sitelib}/quipucordsctl-*.egg-info/
%else
  %{python3_sitelib}/quipucordsctl-*.dist-info/
%endif

%changelog
* Wed Sep 17 2025 Alberto Bellotti <abellott@redhat.com> - 0:2.1.0-1
- Initial version
