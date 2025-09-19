%global product_name_lower quipucords
%global product_name_title Quipucords
%global version_installer 2.1.0
%global server_image quay.io/quipucords/quipucords:2.1
%global ui_image quay.io/quipucords/quipucords-ui:2.1
%global templates_dir src/quipucordsctl/templates

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

Version:        %{version_installer}
Release:        1%{?dist}
Epoch:          0

License:        GPLv3
URL:            https://github.com/quipucords/quipucordsctl
Source0:        %{url}/archive/%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  sed
%if 0%{?fedora} >= 41 || 0%{?rhel} >= 9
BuildRequires:  pyproject-rpm-macros
%endif
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-wheel
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python3-babel

Requires:       bash
Requires:       coreutils
Requires:       podman >= 4.9.4
Requires:       python3-podman
Requires:       python%{python3_pkgversion}

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
python%{python3_pkgversion} -m ensurepip
python%{python3_pkgversion} -m pip install wheel setuptools
# Compile the message catalogs
%if 0%{?rhel} == 8
    python%{python3_pkgversion} -m venv --system-site-packages translations-env
    source translations-env/bin/activate
    ## python%{python3_pkgversion} -m pip install babel
    python%{python3_pkgversion} scripts/translations.py compile
    deactivate
    rm -rf translations-env
%else
    # python%{python3_pkgversion} -m venv --system-site-packages translations-env

    python%{python3_pkgversion} scripts/translations.py compile

    ## python%{python3_pkgversion} -m venv --system-site-packages translations-env
    ## source translations-env/bin/activate
    ## python%{python3_pkgversion} -m pip install babel
    ## python%{python3_pkgversion} scripts/translations.py compile
    ## rm -rf translations-env

    # python%{python3_pkgversion} -m venv --system-site-packages translations-env
    # source translations-env/bin/activate
    # python%{python3_pkgversion} -m pip install babel
    # echo "--------------------------------------------------------------------"
    # echo "The translations-env directory contains ...."
    # ls -1R translations-env
    # echo "--------------------------------------------------------------------"
    # echo "The /usr/lib/python3.12/site-packages contains ...."
    # ls -1R /usr/lib/python3.12/site-packages
    # echo "--------------------------------------------------------------------"
    # translations-env/bin/pybabel compile -d src/quipucordsctl/locale -D messages
    # python%{python3_pkgversion} scripts/translations.py compile
    # deactivate
    # rm -rf %{_builddir}/quipucordsctl-%{version}/translations-env
%endif

%if 0%{?rhel} == 8
    %py3_build
%else
    %pyproject_wheel
%endif

%install
%if 0%{?rhel} == 8
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
%{python3_sitelib}/%{name}/
%if 0%{?rhel} == 8
  %{python3_sitelib}/%{name}-*.egg-info/
%else
  %{python3_sitelib}/%{name}-*.dist-info/
%endif

%changelog
* Wed Sep 17 2025 Alberto Bellotti <abellott@redhat.com> - 0:2.1.0-1
- Initial version
