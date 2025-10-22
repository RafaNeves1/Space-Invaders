import pygame
import random
import math
import sys

# ----- Configuration -----
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
PLAYER_SPEED = 5
BULLET_SPEED = 10
ENEMY_SPEED_X = 1.0
ENEMY_SPEED_Y = 20
ENEMY_ROWS = 4
ENEMY_COLS = 8
ENEMY_HORIZONTAL_PADDING = 60
ENEMY_VERTICAL_PADDING = 40
ENEMY_START_Y = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER_COLOR = (50, 200, 255)
ENEMY_COLOR = (255, 100, 100)
BULLET_COLOR = (255, 255, 0)
TEXT_COLOR = (230, 230, 230)

# ----- Game objects -----
class Player:
    def __init__(self, x, y, w=50, h=20):
        self.rect = pygame.Rect(0,0,w,h)
        self.rect.centerx = x
        self.rect.bottom = y
        self.speed = PLAYER_SPEED
        self.cooldown = 0  # frames until next shot allowed
        self.cooldown_time = 10

    def move(self, dx):
        self.rect.x += dx * self.speed
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))

    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1

    def can_shoot(self):
        return self.cooldown == 0

    def shoot(self):
        self.cooldown = self.cooldown_time
        # spawn bullet from top center of player
        bx = self.rect.centerx
        by = self.rect.top
        return Bullet(bx, by, -BULLET_SPEED, owner='player')

class Enemy:
    def __init__(self, x, y, size=34):
        self.rect = pygame.Rect(0,0,size,size)
        self.rect.center = (x, y)
        self.alive = True

    def draw(self, surf):
        if not self.alive:
            return
        # simple alien shape (triangle + rect)
        cx, cy = self.rect.center
        w = self.rect.width
        h = self.rect.height
        points = [(cx, cy - h//2), (cx - w//2, cy + h//3), (cx + w//2, cy + h//3)]
        pygame.draw.polygon(surf, ENEMY_COLOR, points)
        pygame.draw.rect(surf, ENEMY_COLOR, (self.rect.left + w*0.2, cy, w*0.6, h*0.18))

class Bullet:
    def __init__(self, x, y, vy, owner='player', w=4, h=10):
        self.rect = pygame.Rect(0,0,w,h)
        self.rect.centerx = x
        self.rect.centery = y
        self.vy = vy
        self.owner = owner  # 'player' or 'enemy'

    def update(self):
        self.rect.y += self.vy

    def draw(self, surf):
        pygame.draw.rect(surf, BULLET_COLOR, self.rect)

# ----- Helper functions -----

def create_enemies(rows, cols):
    enemies = []
    total_width = (cols - 1) * ENEMY_HORIZONTAL_PADDING
    start_x = (SCREEN_WIDTH - total_width) / 2
    for row in range(rows):
        for col in range(cols):
            x = start_x + col * ENEMY_HORIZONTAL_PADDING
            y = ENEMY_START_Y + row * ENEMY_VERTICAL_PADDING
            enemies.append(Enemy(x, y))
    return enemies

def any_enemies_alive(enemies):
    return any(e.alive for e in enemies)

# Collision check helper (rectangle-based)
def check_collision(a, b):
    return a.rect.colliderect(b.rect)

# ----- Main Game -----

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Space Invaders - Pygame')
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 28)
    big_font = pygame.font.SysFont(None, 56)

    def reset_game():
        player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)
        enemies = create_enemies(ENEMY_ROWS, ENEMY_COLS)
        bullets = []
        enemy_direction = 1  # 1 -> right, -1 -> left
        enemy_speed_x = ENEMY_SPEED_X
        score = 0
        wave = 1
        game_over = False
        win = False
        return {
            'player': player,
            'enemies': enemies,
            'bullets': bullets,
            'enemy_direction': enemy_direction,
            'enemy_speed_x': enemy_speed_x,
            'score': score,
            'wave': wave,
            'game_over': game_over,
            'win': win,
        }

    state = reset_game()

    running = True
    shoot_pressed = False
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key in (pygame.K_SPACE, pygame.K_k):
                    shoot_pressed = True
                if event.key == pygame.K_r and state['game_over']:
                    state = reset_game()
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_k):
                    shoot_pressed = False

        keys = pygame.key.get_pressed()
        if not state['game_over']:
            dx = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            state['player'].move(dx)
            state['player'].update()

            # Shooting
            if shoot_pressed and state['player'].can_shoot():
                state['bullets'].append(state['player'].shoot())

            # Update bullets
            for b in state['bullets']:
                b.update()
            # remove offscreen bullets
            state['bullets'] = [b for b in state['bullets'] if -50 <= b.rect.y <= SCREEN_HEIGHT + 50]

            # Enemy movement
            # move horizontally; if any hits edge, flip direction and lower
            alive_enemies = [e for e in state['enemies'] if e.alive]
            if alive_enemies:
                leftmost = min(e.rect.left for e in alive_enemies)
                rightmost = max(e.rect.right for e in alive_enemies)
                dir = state['enemy_direction']
                move_x = dir * state['enemy_speed_x']
                # check edge collision
                hit_edge = False
                if rightmost + move_x >= SCREEN_WIDTH - 5 and dir == 1:
                    hit_edge = True
                if leftmost + move_x <= 5 and dir == -1:
                    hit_edge = True
                if hit_edge:
                    # lower and reverse
                    for e in alive_enemies:
                        e.rect.y += ENEMY_SPEED_Y
                    state['enemy_direction'] *= -1
                else:
                    for e in alive_enemies:
                        e.rect.x += move_x

            # Enemy shooting (random)
            # Occasionally spawn enemy bullets from a random alive enemy
            if random.random() < 0.02 and alive_enemies:
                shooter = random.choice(alive_enemies)
                bx = shooter.rect.centerx
                by = shooter.rect.bottom
                state['bullets'].append(Bullet(bx, by, BULLET_SPEED, owner='enemy'))

            # Bullet collisions
            for b in state['bullets'][:]:
                if b.owner == 'player':
                    for e in state['enemies']:
                        if e.alive and check_collision(b, e):
                            e.alive = False
                            try:
                                state['bullets'].remove(b)
                            except ValueError:
                                pass
                            state['score'] += 10
                            break
                else:  # enemy bullet
                    if check_collision(b, state['player']):
                        state['game_over'] = True
                        state['win'] = False

            # Check if any enemy reached the player's level
            for e in state['enemies']:
                if e.alive and e.rect.bottom >= state['player'].rect.top:
                    state['game_over'] = True
                    state['win'] = False

            # Check wave clear
            if not any_enemies_alive(state['enemies']):
                # advance to next wave: recreate enemies, increase speed slightly
                state['wave'] += 1
                state['enemy_speed_x'] *= 1.12
                # create new enemies slightly closer
                state['enemies'] = create_enemies(ENEMY_ROWS, ENEMY_COLS)
                # give small bonus
                state['score'] += 50

        # Draw
        screen.fill(BLACK)

        # Draw player
        p = state['player']
        pygame.draw.rect(screen, PLAYER_COLOR, p.rect)
        # draw player 'gun'
        pygame.draw.rect(screen, PLAYER_COLOR, (p.rect.centerx - 4, p.rect.top - 8, 8, 8))

        # Draw enemies
        for e in state['enemies']:
            e.draw(screen)

        # Draw bullets
        for b in state['bullets']:
            b.draw(screen)

        # UI: score and wave
        score_surf = font.render(f'Score: {state["score"]}', True, TEXT_COLOR)
        wave_surf = font.render(f'Wave: {state["wave"]}', True, TEXT_COLOR)
        screen.blit(score_surf, (10, 10))
        screen.blit(wave_surf, (10, 34))

        if state['game_over']:
            text = 'YOU WIN!' if state['win'] else 'GAME OVER'
            t_surf = big_font.render(text, True, TEXT_COLOR)
            sub_surf = font.render('Press R to restart', True, TEXT_COLOR)
            screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20)))
            screen.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30)))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
