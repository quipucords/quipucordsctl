%global product_name_lower quipucords
%global product_name_title Quipucords
%global version_installer 2.1.0
%global server_image quay.io/quipucords/quipucords:2.1
%global ui_image quay.io/quipucords/quipucords-ui:2.1
%global templates_dir src/quipucordsctl/templates

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
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-wheel
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python3-babel
BuildRequires:  babel

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
python%{python3_pkgversion} scripts/translations.py compile    # Compile the message catalogs

%pyproject_wheel

%install
%pyproject_install
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
%{python3_sitelib}/%{name}-*.dist-info/

%changelog
* Fri Sep 12 2025 Alberto Bellotti <abellott@redhat.com> - 0:2.1.0-1
- Initial version
