{ pkgs, ... }: {

  channel = "unstable";

  packages = [
    pkgs.python313
    pkgs.docker
    pkgs.docker-compose
    pkgs.uv
  ];

  env = {
    DJANGO_SETTINGS_MODULE = "config.settings";
  };

  idx = {
    extensions = [
      "ms-python.python"
      "ms-azuretools.vscode-docker"
      "alefragnani.Bookmarks"
      "batisteo.vscode-django"
      "charliermarsh.ruff"
      "esbenp.prettier-vscode"
      "monosans.djlint"
      "ms-azuretools.vscode-containers"
      "ms-python.debugpy"
    ];

    previews = {
      enable = true;
      previews = {
        web = {
          # コンテナ起動時に IDX の $PORT を流し込む
          command = [ "sh" "-c" "PORT=$PORT docker compose up" ];
          manager = "web";
          env = {
            PORT = "$PORT";
          };
        };
      };
    };
  };
  services.docker.enable = true;
}
